"""Offline indexing pipeline from chunks.jsonl to embeddings, BM25, and Qdrant."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from backend.ingestion.hashing import sha256_text

from .bm25_index import build_bm25
from .config import BM25Config, EmbeddingConfig, IndexingConfig, QdrantConfig
from .corpus import eligible_chunks, load_corpus_manifest, load_documents, skipped_documents, source_manifest_hash
from .embeddings import generate_embeddings, load_embedding_cache
from .io import read_json
from .manifest import build_index_manifest, write_index_manifest
from .models import EmbeddingRecord
from .qdrant_index import QdrantRestClient, sync_qdrant
from .validation import validate_index, write_validation_reports

LOG = logging.getLogger(__name__)


def build_indexes(
    *,
    config: IndexingConfig,
    rebuild: bool = False,
    skip_embeddings: bool = False,
    skip_bm25: bool = False,
    skip_qdrant: bool = False,
) -> dict[str, Any]:
    chunks_path = config.chunks_path.resolve()
    output_dir = config.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    all_chunks_count = sum(1 for _ in chunks_path.open(encoding="utf-8") if _.strip())
    chunks, skipped_chunks, collisions = eligible_chunks(chunks_path, index_collision_documents=config.index_collision_documents)
    documents = load_documents(chunks_path)
    skipped_docs = skipped_documents(documents, chunks, skipped_chunks)
    collision_docs = sorted(collisions)
    LOG.info("Chunks discovered: %d", all_chunks_count)
    LOG.info("Eligible chunks: %d", len(chunks))
    LOG.info("Skipped chunks: %d", len(skipped_chunks))
    LOG.info("Collision documents: %d", len(collision_docs))

    embeddings: list[EmbeddingRecord] = []
    embed_stats = {"cache_hits": 0, "cache_misses": 0, "embedding_dimension": 0}
    if not skip_embeddings:
        embeddings, embed_stats = generate_embeddings(chunks, config.embedding, output_dir, rebuild=rebuild)
        LOG.info("Embeddings generated/reused: %d", len(embeddings))
        LOG.info("Embedding cache hits: %d", embed_stats["cache_hits"])
        LOG.info("Embedding cache misses: %d", embed_stats["cache_misses"])
    else:
        embeddings = list(load_embedding_cache(output_dir / "embeddings" / "embeddings.jsonl").values())
        if embeddings:
            embed_stats["embedding_dimension"] = embeddings[0].embedding_dimension

    bm25_metadata = None
    if not skip_bm25:
        bm25_metadata = build_bm25(chunks, config.bm25, output_dir)
        LOG.info("BM25 records: %d", bm25_metadata["indexed_chunks"])

    qdrant_points: int | None = None
    qdrant_client = None
    if not skip_qdrant:
        if not embeddings:
            raise RuntimeError("Qdrant indexing requires embeddings. Remove --skip-embeddings or provide cached embeddings.")
        embeddings_by_chunk = {record.chunk_id: record.embedding for record in embeddings}
        qdrant_points = sync_qdrant(
            chunks,
            embeddings_by_chunk,
            config.qdrant,
            vector_size=embed_stats["embedding_dimension"],
            embedding_model=config.embedding.model,
        )
        qdrant_client = QdrantRestClient(config.qdrant)
        LOG.info("Qdrant points: %d", qdrant_points)

    corpus_manifest = load_corpus_manifest(chunks_path) or {}
    manifest = build_index_manifest(
        corpus_id=corpus_manifest.get("corpus_id", "SIH26045"),
        source_corpus_manifest_hash=source_manifest_hash(chunks_path),
        embedding_config=config.embedding,
        bm25_config=config.bm25,
        qdrant_config=config.qdrant,
        embedding_dimension=embed_stats["embedding_dimension"],
        total_source_chunks=all_chunks_count,
        embedded_chunks=len(embeddings),
        bm25_indexed_chunks=bm25_metadata["indexed_chunks"] if bm25_metadata else 0,
        qdrant_points=qdrant_points,
        skipped_chunks=skipped_chunks,
        skipped_documents=skipped_docs,
        collision_documents=collision_docs,
        model_revision=embeddings[0].model_revision if embeddings else config.embedding.revision,
        qdrant_enabled=not skip_qdrant,
    )
    write_index_manifest(output_dir, manifest)
    messages = validate_index(
        chunks=chunks,
        embeddings=embeddings,
        bm25_metadata=bm25_metadata,
        index_manifest=manifest,
        output_dir=output_dir,
        qdrant_client=qdrant_client,
        source_manifest_path=chunks_path.parent / "corpus_manifest.json",
    )
    write_validation_reports(output_dir, messages)
    return {
        "chunks": chunks,
        "embeddings": embeddings,
        "bm25_metadata": bm25_metadata,
        "manifest": manifest,
        "validation_messages": messages,
        "embedding_stats": embed_stats,
    }


def validate_existing(config: IndexingConfig) -> dict[str, Any]:
    chunks, skipped_chunks, collisions = eligible_chunks(config.chunks_path, index_collision_documents=config.index_collision_documents)
    manifest = read_json(config.output_dir / "index_manifest.json")
    embeddings = list(load_embedding_cache(config.output_dir / "embeddings" / "embeddings.jsonl").values())
    bm25_metadata = read_json(config.output_dir / "bm25" / "metadata.json") if (config.output_dir / "bm25" / "metadata.json").exists() else None
    qdrant_client = QdrantRestClient(config.qdrant) if manifest.get("qdrant_enabled") else None
    messages = validate_index(
        chunks=chunks,
        embeddings=embeddings,
        bm25_metadata=bm25_metadata,
        index_manifest=manifest,
        output_dir=config.output_dir,
        qdrant_client=qdrant_client,
        source_manifest_path=config.chunks_path.parent / "corpus_manifest.json",
    )
    write_validation_reports(config.output_dir, messages)
    return {"manifest": manifest, "validation_messages": messages, "skipped_chunks": skipped_chunks, "collision_documents": sorted(collisions)}


def config_with_overrides(
    base: IndexingConfig,
    *,
    chunks: Path | None = None,
    output: Path | None = None,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
    device: str | None = None,
    batch_size: int | None = None,
    qdrant_mode: str | None = None,
    qdrant_url: str | None = None,
    qdrant_collection: str | None = None,
    qdrant_distance: str | None = None,
    qdrant_upsert_batch_size: int | None = None,
    index_collision_documents: bool | None = None,
) -> IndexingConfig:
    embedding = replace(
        base.embedding,
        provider=embedding_provider or base.embedding.provider,
        model=embedding_model or base.embedding.model,
        device=device or base.embedding.device,
        batch_size=batch_size or base.embedding.batch_size,
    )
    qdrant = replace(
        base.qdrant,
        mode=qdrant_mode or base.qdrant.mode,
        url=qdrant_url or base.qdrant.url,
        collection_name=qdrant_collection or base.qdrant.collection_name,
        distance=qdrant_distance or base.qdrant.distance,
        upsert_batch_size=qdrant_upsert_batch_size or base.qdrant.upsert_batch_size,
    )
    return replace(
        base,
        chunks_path=chunks or base.chunks_path,
        output_dir=output or base.output_dir,
        embedding=embedding,
        qdrant=qdrant,
        index_collision_documents=base.index_collision_documents if index_collision_documents is None else index_collision_documents,
    )
