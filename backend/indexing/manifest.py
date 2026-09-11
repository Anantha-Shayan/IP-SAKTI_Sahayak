"""Index manifest writer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import INDEXING_VERSION, BM25Config, EmbeddingConfig, QdrantConfig
from .io import write_json


def build_index_manifest(
    *,
    corpus_id: str,
    source_corpus_manifest_hash: str,
    embedding_config: EmbeddingConfig,
    bm25_config: BM25Config,
    qdrant_config: QdrantConfig,
    embedding_dimension: int,
    total_source_chunks: int,
    embedded_chunks: int,
    bm25_indexed_chunks: int,
    qdrant_points: int | None,
    skipped_chunks: list[dict[str, Any]],
    skipped_documents: list[dict[str, Any]],
    collision_documents: list[str],
    model_revision: str | None,
    qdrant_enabled: bool,
) -> dict[str, Any]:
    return {
        "indexing_version": INDEXING_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_id": corpus_id,
        "source_corpus_manifest_hash": source_corpus_manifest_hash,
        "embedding_provider": embedding_config.provider,
        "embedding_model": embedding_config.model,
        "embedding_model_revision": model_revision,
        "embedding_device": embedding_config.device,
        "embedding_dimension": embedding_dimension,
        "embedding_normalize": embedding_config.normalize,
        "embedding_input_field": "embedding_text",
        "total_source_chunks": total_source_chunks,
        "embedded_chunks": embedded_chunks,
        "bm25_indexed_chunks": bm25_indexed_chunks,
        "qdrant_enabled": qdrant_enabled,
        "qdrant_points": qdrant_points,
        "skipped_chunks": skipped_chunks,
        "skipped_documents": skipped_documents,
        "collision_documents": collision_documents,
        "index_collision_documents": len([d for d in skipped_chunks if d.get("reason") == "content_collision"]) == 0,
        "bm25": {
            "k1": bm25_config.k1,
            "b": bm25_config.b,
            "lowercase": bm25_config.lowercase,
            "remove_stopwords": bm25_config.remove_stopwords,
            "tokenizer_version": bm25_config.tokenizer_version,
        },
        "qdrant": {
            "mode": qdrant_config.mode,
            "url": qdrant_config.url,
            "collection_name": qdrant_config.collection_name,
            "distance": qdrant_config.distance,
            "upsert_batch_size": qdrant_config.upsert_batch_size,
        },
    }


def write_index_manifest(output_dir: Path, manifest: dict[str, Any]) -> None:
    write_json(output_dir / "index_manifest.json", manifest)

