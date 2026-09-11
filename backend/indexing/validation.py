"""Index-stage validation."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .config import INDEXING_VERSION
from .corpus import source_manifest_hash
from .embeddings import embedding_input_hash
from .io import read_json, write_json
from .models import EmbeddingRecord, ValidationMessage
from .qdrant_index import QdrantRestClient


def validate_index(
    *,
    chunks: list[dict[str, Any]],
    embeddings: list[EmbeddingRecord],
    bm25_metadata: dict[str, Any] | None,
    index_manifest: dict[str, Any],
    output_dir: Path,
    qdrant_client: QdrantRestClient | None = None,
    source_manifest_path: Path | None = None,
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    chunk_id_set = set(chunk_ids)
    if len(chunk_ids) != len(chunk_id_set):
        messages.append(ValidationMessage("CRITICAL", "DUPLICATE_CHUNK_IDS", "Eligible chunks contain duplicate chunk_id values."))
    emb_ids = [record.chunk_id for record in embeddings]
    if len(emb_ids) != len(set(emb_ids)):
        messages.append(ValidationMessage("CRITICAL", "DUPLICATE_EMBEDDED_CHUNK_IDS", "Embedding records contain duplicate chunk_id values."))
    if set(emb_ids) != chunk_id_set:
        messages.append(ValidationMessage("CRITICAL", "EMBEDDING_CHUNK_ID_MISMATCH", "Embedding records do not match eligible chunk IDs."))
    expected_dim = index_manifest.get("embedding_dimension", 0)
    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    for record in embeddings:
        if record.embedding_dimension != expected_dim or len(record.embedding) != expected_dim:
            messages.append(ValidationMessage("CRITICAL", "EMBEDDING_DIMENSION_MISMATCH", "Embedding dimension does not match manifest.", chunk_id=record.chunk_id))
        if record.embedding_provider != index_manifest.get("embedding_provider"):
            messages.append(ValidationMessage("CRITICAL", "EMBEDDING_PROVIDER_MISMATCH", "Embedding provider does not match manifest.", chunk_id=record.chunk_id))
        if record.embedding_model != index_manifest.get("embedding_model"):
            messages.append(ValidationMessage("CRITICAL", "EMBEDDING_MODEL_MISMATCH", "Embedding model does not match manifest.", chunk_id=record.chunk_id))
        if record.model_revision != index_manifest.get("embedding_model_revision"):
            messages.append(ValidationMessage("CRITICAL", "EMBEDDING_REVISION_MISMATCH", "Embedding model revision does not match manifest.", chunk_id=record.chunk_id))
        if record.normalized != index_manifest.get("embedding_normalize"):
            messages.append(ValidationMessage("CRITICAL", "EMBEDDING_NORMALIZATION_MISMATCH", "Embedding normalization setting does not match manifest.", chunk_id=record.chunk_id))
        if any(not isinstance(x, int | float) or math.isnan(x) or math.isinf(x) for x in record.embedding):
            messages.append(ValidationMessage("CRITICAL", "INVALID_EMBEDDING_VALUE", "Embedding contains NaN or infinite value.", chunk_id=record.chunk_id))
        chunk = chunks_by_id.get(record.chunk_id)
        if chunk and embedding_input_hash(chunk["embedding_text"]) != record.embedding_input_sha256:
            messages.append(ValidationMessage("CRITICAL", "EMBEDDING_INPUT_HASH_MISMATCH", "Embedding input hash does not match chunk embedding_text.", chunk_id=record.chunk_id))
    if bm25_metadata is not None:
        if bm25_metadata.get("indexed_chunks") != len(chunks):
            messages.append(ValidationMessage("CRITICAL", "BM25_COUNT_MISMATCH", "BM25 indexed chunk count does not match eligible chunk count."))
        if bm25_metadata.get("chunk_id_by_position") != chunk_ids:
            messages.append(ValidationMessage("CRITICAL", "BM25_CHUNK_ORDER_MISMATCH", "BM25 chunk_id order does not match eligible chunk order."))
        bm25_index_path = output_dir / "bm25" / "index" / "bm25_index.json"
        if bm25_index_path.exists():
            bm25_index = read_json(bm25_index_path)
            if bm25_index.get("metadata", {}).get("chunk_id_by_position") != chunk_ids:
                messages.append(ValidationMessage("CRITICAL", "BM25_INDEX_CHUNK_ORDER_MISMATCH", "BM25 index chunk_id order does not match eligible chunk order."))
            if len(bm25_index.get("document_lengths", [])) != len(chunks) or len(bm25_index.get("term_frequencies", [])) != len(chunks):
                messages.append(ValidationMessage("CRITICAL", "BM25_INDEX_COUNT_MISMATCH", "BM25 index arrays do not match eligible chunk count."))
        else:
            messages.append(ValidationMessage("CRITICAL", "BM25_INDEX_MISSING", "BM25 index file is missing."))
    for chunk in chunks:
        if not chunk.get("text", "").strip():
            messages.append(ValidationMessage("CRITICAL", "ZERO_LENGTH_TEXT_INDEXED", "Zero-length chunk text was indexed.", chunk_id=chunk["chunk_id"]))
        provenance = chunk.get("provenance") or {}
        if not provenance.get("relative_path") or provenance.get("pdf_page_start") is None or provenance.get("pdf_page_end") is None:
            messages.append(ValidationMessage("CRITICAL", "INVALID_PROVENANCE", "Indexed chunk lacks required provenance.", chunk_id=chunk["chunk_id"], document_id=chunk.get("document_id")))
    source_manifest_path = source_manifest_path or output_dir.parent / "embedding_ready" / "corpus_manifest.json"
    if source_manifest_path.exists():
        source_manifest = read_json(source_manifest_path)
        if source_manifest.get("corpus_id") != index_manifest.get("corpus_id"):
            messages.append(ValidationMessage("CRITICAL", "SOURCE_CORPUS_MISMATCH", "Source corpus manifest corpus_id differs from index manifest."))
        actual_source_hash = source_manifest_hash(source_manifest_path.parent / "chunks.jsonl")
        if actual_source_hash != index_manifest.get("source_corpus_manifest_hash"):
            messages.append(ValidationMessage("CRITICAL", "SOURCE_CORPUS_MANIFEST_HASH_MISMATCH", "Source corpus manifest hash differs from index manifest."))
    elif index_manifest.get("source_corpus_manifest_hash"):
        messages.append(ValidationMessage("CRITICAL", "SOURCE_CORPUS_MANIFEST_MISSING", "Source corpus manifest is missing."))
    if qdrant_client is not None and index_manifest.get("qdrant_enabled"):
        expected = len(chunks)
        actual = qdrant_client.count()
        if actual != expected:
            messages.append(ValidationMessage("CRITICAL", "QDRANT_COUNT_MISMATCH", f"Qdrant has {actual} points, expected {expected}."))
        payloads = qdrant_client.iter_payloads()
        for payload in payloads:
            if "chunk_id" not in payload:
                messages.append(ValidationMessage("CRITICAL", "QDRANT_PAYLOAD_MISSING_CHUNK_ID", "Qdrant payload is missing chunk_id."))
            elif payload["chunk_id"] not in chunk_id_set:
                messages.append(ValidationMessage("CRITICAL", "QDRANT_UNKNOWN_CHUNK_ID", "Qdrant payload chunk_id is not in eligible chunks.", chunk_id=payload["chunk_id"]))
        payload_chunk_ids = {payload.get("chunk_id") for payload in payloads if payload.get("chunk_id")}
        if payload_chunk_ids != chunk_id_set:
            messages.append(ValidationMessage("CRITICAL", "QDRANT_PAYLOAD_CHUNK_ID_MISMATCH", "Qdrant payload chunk IDs do not match eligible chunk IDs."))
    if not any(m.severity == "CRITICAL" for m in messages):
        messages.append(ValidationMessage("INFO", "INDEX_VALIDATION_PASS", "Index validation completed without critical errors."))
    return messages


def validation_status(messages: list[ValidationMessage]) -> str:
    if any(m.severity == "CRITICAL" for m in messages):
        return "FAILED"
    if any(m.severity == "WARNING" for m in messages):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def write_validation_reports(output_dir: Path, messages: list[ValidationMessage]) -> None:
    counts = {
        "critical": sum(1 for m in messages if m.severity == "CRITICAL"),
        "warning": sum(1 for m in messages if m.severity == "WARNING"),
        "info": sum(1 for m in messages if m.severity == "INFO"),
    }
    data = {
        "indexing_version": INDEXING_VERSION,
        "validation_status": validation_status(messages),
        "counts": counts,
        "messages": [m.to_json() for m in messages],
    }
    write_json(output_dir / "index_validation_report.json", data)
    lines = [
        f"Validation status: {data['validation_status']}",
        f"CRITICAL: {counts['critical']}",
        f"WARNING: {counts['warning']}",
        f"INFO: {counts['info']}",
        "",
    ]
    for severity in ["CRITICAL", "WARNING", "INFO"]:
        selected = [m for m in messages if m.severity == severity]
        if selected:
            lines.append(f"{severity}:")
            lines.extend(f"- [{m.code}] {m.message}" for m in selected)
            lines.append("")
    (output_dir / "index_validation_report.txt").write_text("\n".join(lines), encoding="utf-8")
