"""Configurable embedding generation and deterministic cache."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Iterable, Protocol

from backend.ingestion.hashing import sha256_text

from .config import EmbeddingConfig, INDEXING_VERSION
from .models import EmbeddingRecord


class Embedder(Protocol):
    dimension: int
    model_revision: str | None

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...


class SentenceTransformerEmbedder:
    def __init__(self, config: EmbeddingConfig) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise RuntimeError("EMBEDDING_PROVIDER=sentence_transformers requires sentence-transformers. Install the indexing requirements.") from exc
        kwargs = {"device": config.device}
        if config.revision:
            kwargs["revision"] = config.revision
        self.model = SentenceTransformer(config.model, **kwargs)
        self.normalize = config.normalize
        self.dimension = int(self.model.get_sentence_embedding_dimension())
        self.model_revision = config.revision

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, batch_size=len(texts), normalize_embeddings=self.normalize, show_progress_bar=True)
        return [[float(x) for x in vec] for vec in vectors]


class DeterministicHashEmbedder:
    """Small deterministic dense-vector provider for offline tests and no-network environments."""

    def __init__(self, config: EmbeddingConfig, dimension: int = 128) -> None:
        self.config = config
        self.dimension = int(config.model.rsplit("-", 1)[-1]) if config.model.startswith("hash-") and config.model.rsplit("-", 1)[-1].isdigit() else dimension
        self.model_revision = config.revision or "deterministic"

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            rng = random.Random(sha256_text(self.config.model, text))
            vec = [rng.uniform(-1.0, 1.0) for _ in range(self.dimension)]
            if self.config.normalize:
                norm = math.sqrt(sum(x * x for x in vec)) or 1.0
                vec = [x / norm for x in vec]
            vectors.append([float(x) for x in vec])
        return vectors


def make_embedder(config: EmbeddingConfig) -> Embedder:
    if config.provider == "sentence_transformers":
        return SentenceTransformerEmbedder(config)
    if config.provider in {"deterministic_hash", "hash"}:
        return DeterministicHashEmbedder(config)
    raise ValueError(f"Unsupported embedding provider: {config.provider}")


def embedding_input_hash(text: str) -> str:
    return sha256_text(text)


def embedding_cache_key(chunk_id: str, input_hash: str, config: EmbeddingConfig, model_revision: str | None) -> str:
    return sha256_text(chunk_id, input_hash, config.provider, config.model, model_revision, config.normalize)


def load_embedding_cache(cache_path: Path) -> dict[str, EmbeddingRecord]:
    if not cache_path.exists():
        return {}
    records: dict[str, EmbeddingRecord] = {}
    with cache_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            records[row["cache_key"]] = EmbeddingRecord(**row)
    return records


def write_embedding_records(path: Path, records: Iterable[EmbeddingRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record.to_json(), ensure_ascii=False, sort_keys=True) + "\n")


def generate_embeddings(
    chunks: list[dict],
    config: EmbeddingConfig,
    output_dir: Path,
    *,
    rebuild: bool = False,
) -> tuple[list[EmbeddingRecord], dict[str, int]]:
    embeddings_path = output_dir / "embeddings" / "embeddings.jsonl"
    cache = {} if rebuild else load_embedding_cache(embeddings_path)
    embedder = make_embedder(config)
    records_by_chunk: dict[str, EmbeddingRecord] = {}
    hits = 0
    misses = 0
    batch: list[dict] = []

    def flush() -> None:
        nonlocal misses
        if not batch:
            return
        vectors = embedder.encode([item["embedding_text"] for item in batch])
        for item, vector in zip(batch, vectors, strict=True):
            rec = EmbeddingRecord(
                chunk_id=item["chunk_id"],
                cache_key=item["cache_key"],
                embedding_model=config.model,
                embedding_provider=config.provider,
                embedding_dimension=embedder.dimension,
                embedding=vector,
                embedding_input_sha256=item["input_hash"],
                normalized=config.normalize,
                model_revision=embedder.model_revision,
                indexing_version=INDEXING_VERSION,
            )
            records_by_chunk[item["chunk_id"]] = rec
            misses += 1
        batch.clear()

    for chunk in chunks:
        input_hash = embedding_input_hash(chunk["embedding_text"])
        key = embedding_cache_key(chunk["chunk_id"], input_hash, config, embedder.model_revision)
        cached = cache.get(key)
        if (
            cached
            and cached.cache_key == key
            and cached.embedding_input_sha256 == input_hash
            and cached.embedding_provider == config.provider
            and cached.embedding_model == config.model
            and cached.model_revision == embedder.model_revision
            and cached.normalized == config.normalize
            and cached.embedding_dimension == embedder.dimension
            and len(cached.embedding) == embedder.dimension
            and cached.indexing_version == INDEXING_VERSION
        ):
            records_by_chunk[chunk["chunk_id"]] = cached
            hits += 1
            continue
        batch.append({"chunk_id": chunk["chunk_id"], "embedding_text": chunk["embedding_text"], "input_hash": input_hash, "cache_key": key})
        if len(batch) >= config.batch_size:
            flush()
    flush()
    ordered = [records_by_chunk[chunk["chunk_id"]] for chunk in chunks]
    write_embedding_records(embeddings_path, ordered)
    return ordered, {"cache_hits": hits, "cache_misses": misses, "embedding_dimension": ordered[0].embedding_dimension if ordered else 0}
