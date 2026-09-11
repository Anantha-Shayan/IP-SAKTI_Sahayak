"""Indexing configuration loaded from environment and CLI overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

INDEXING_VERSION = "1.0.0"


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
    model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    device: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    normalize: bool = _bool_env("EMBEDDING_NORMALIZE", True)
    revision: str | None = os.getenv("EMBEDDING_MODEL_REVISION")


@dataclass(frozen=True)
class BM25Config:
    k1: float = float(os.getenv("BM25_K1", "1.5"))
    b: float = float(os.getenv("BM25_B", "0.75"))
    lowercase: bool = _bool_env("BM25_LOWERCASE", True)
    remove_stopwords: bool = _bool_env("BM25_REMOVE_STOPWORDS", False)
    tokenizer_version: str = "legal-tokenizer-v1"


@dataclass(frozen=True)
class QdrantConfig:
    mode: str = os.getenv("QDRANT_MODE", "local")
    url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key: str | None = os.getenv("QDRANT_API_KEY")
    collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "sih26045_chunks")
    distance: str = os.getenv("QDRANT_DISTANCE", "Cosine")
    upsert_batch_size: int = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "128"))
    timeout_seconds: int = int(os.getenv("QDRANT_TIMEOUT_SECONDS", "60"))


@dataclass(frozen=True)
class IndexingConfig:
    chunks_path: Path = Path(os.getenv("INDEX_CHUNKS_PATH", "data/processed/embedding_ready/chunks.jsonl"))
    output_dir: Path = Path(os.getenv("INDEX_OUTPUT_DIR", "data/processed/indexes"))
    index_collision_documents: bool = _bool_env("INDEX_COLLISION_DOCUMENTS", True)
    embedding: EmbeddingConfig = EmbeddingConfig()
    bm25: BM25Config = BM25Config()
    qdrant: QdrantConfig = QdrantConfig()

