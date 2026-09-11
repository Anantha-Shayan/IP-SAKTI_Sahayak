from __future__ import annotations

import json
from pathlib import Path

from backend.ingestion.hashing import sha256_text
from backend.indexing.bm25_index import build_bm25, tokenize_legal_text
from backend.indexing.config import BM25Config, EmbeddingConfig, IndexingConfig, QdrantConfig
from backend.indexing.corpus import eligible_chunks
from backend.indexing.embeddings import generate_embeddings
from backend.indexing.manifest import build_index_manifest
from backend.indexing.models import EmbeddingRecord
from backend.indexing.validation import validate_index


def test_collision_documents_excluded_when_config_false(tmp_path: Path) -> None:
    base = tmp_path / "embedding_ready"
    base.mkdir()
    chunks = [
        _chunk("c1", "doc1", "Dataset_1/Patents_Act_1970_Updated.pdf"),
        _chunk("c2", "doc2", "Dataset_1/Trade_Marks_Act_1999.pdf"),
        _chunk("c3", "doc3", "Dataset_1/Other.pdf"),
    ]
    _write_jsonl(base / "chunks.jsonl", chunks)
    (base / "validation_report.json").write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "code": "CRITICAL_DOCUMENT_CONTENT_COLLISION",
                        "message": "Dataset_1/Patents_Act_1970_Updated.pdf and Dataset_1/Trade_Marks_Act_1999.pdf share 100% identical extracted pages.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    indexed, skipped, collisions = eligible_chunks(base / "chunks.jsonl", index_collision_documents=False)
    assert [c["chunk_id"] for c in indexed] == ["c3"]
    assert {s["chunk_id"] for s in skipped} == {"c1", "c2"}
    assert len(collisions) == 2


def test_index_manifest_generated() -> None:
    manifest = build_index_manifest(
        corpus_id="SIH26045",
        source_corpus_manifest_hash="hash",
        embedding_config=EmbeddingConfig(provider="deterministic_hash", model="hash-8"),
        bm25_config=BM25Config(),
        qdrant_config=QdrantConfig(url="http://localhost:6333"),
        embedding_dimension=8,
        total_source_chunks=3,
        embedded_chunks=3,
        bm25_indexed_chunks=3,
        qdrant_points=3,
        skipped_chunks=[],
        skipped_documents=[],
        collision_documents=["Dataset_1/A.pdf"],
        model_revision="deterministic",
        qdrant_enabled=True,
    )
    assert manifest["indexing_version"]
    assert manifest["embedding_dimension"] == 8
    assert manifest["qdrant"]["collection_name"] == "sih26045_chunks"


def test_index_validation_detects_mismatched_counts(tmp_path: Path) -> None:
    chunks = [_chunk("c1", "doc1", "Dataset_1/A.pdf"), _chunk("c2", "doc1", "Dataset_1/A.pdf")]
    embedding = EmbeddingRecord(
        chunk_id="c1",
        cache_key="k",
        embedding_model="hash-4",
        embedding_provider="deterministic_hash",
        embedding_dimension=4,
        embedding=[0.1, 0.2, 0.3, 0.4],
        embedding_input_sha256="wrong",
        normalized=True,
        model_revision="deterministic",
        indexing_version="1.0.0",
    )
    messages = validate_index(
        chunks=chunks,
        embeddings=[embedding],
        bm25_metadata={"indexed_chunks": 1, "chunk_id_by_position": ["c1"]},
        index_manifest={"embedding_dimension": 4, "corpus_id": "SIH26045", "qdrant_enabled": False},
        output_dir=tmp_path,
    )
    codes = {m.code for m in messages}
    assert "EMBEDDING_CHUNK_ID_MISMATCH" in codes
    assert "BM25_COUNT_MISMATCH" in codes
    assert "EMBEDDING_INPUT_HASH_MISMATCH" in codes


def test_bm25_preserves_legal_tokens_and_chunk_order(tmp_path: Path) -> None:
    chunks = [_chunk("c1", "doc1", "Dataset_1/A.pdf", text="Section 3(1)(a) and Article 5 apply."), _chunk("c2", "doc1", "Dataset_1/A.pdf", text="Rule 12 governs notice.")]
    tokens = tokenize_legal_text(chunks[0]["text"], BM25Config())
    assert "section 3(1)(a)" in tokens
    assert "article 5" in tokens
    metadata = build_bm25(chunks, BM25Config(), tmp_path)
    assert metadata["chunk_id_by_position"] == ["c1", "c2"]
    assert (tmp_path / "bm25" / "index" / "bm25_index.json").exists()


def test_deterministic_hash_embeddings_cache(tmp_path: Path) -> None:
    chunks = [_chunk("c1", "doc1", "Dataset_1/A.pdf"), _chunk("c2", "doc1", "Dataset_1/A.pdf")]
    config = EmbeddingConfig(provider="deterministic_hash", model="hash-16", batch_size=1)
    first, first_stats = generate_embeddings(chunks, config, tmp_path)
    second, second_stats = generate_embeddings(chunks, config, tmp_path)
    assert first_stats["cache_misses"] == 2
    assert second_stats["cache_hits"] == 2
    assert first[0].embedding == second[0].embedding
    assert first[0].embedding_dimension == 16


def test_embedding_cache_invalidates_for_model_change(tmp_path: Path) -> None:
    chunks = [_chunk("c1", "doc1", "Dataset_1/A.pdf")]
    first_config = EmbeddingConfig(provider="deterministic_hash", model="hash-16")
    second_config = EmbeddingConfig(provider="deterministic_hash", model="hash-8")
    first, _ = generate_embeddings(chunks, first_config, tmp_path)
    second, stats = generate_embeddings(chunks, second_config, tmp_path)
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 1
    assert first[0].embedding_dimension == 16
    assert second[0].embedding_dimension == 8


def test_validation_allows_zero_pdf_page_number(tmp_path: Path) -> None:
    chunk = _chunk("c1", "doc1", "Dataset_1/A.pdf")
    chunk["provenance"]["pdf_page_start"] = 0
    chunk["provenance"]["pdf_page_end"] = 0
    embedding = _embedding_for_chunk(chunk)
    messages = validate_index(
        chunks=[chunk],
        embeddings=[embedding],
        bm25_metadata={"indexed_chunks": 1, "chunk_id_by_position": ["c1"]},
        index_manifest=_manifest_for_validation(embedding_dimension=4),
        output_dir=tmp_path,
    )
    assert "INVALID_PROVENANCE" not in {m.code for m in messages}


def test_validation_detects_source_manifest_hash_mismatch(tmp_path: Path) -> None:
    embedding_ready = tmp_path / "embedding_ready"
    output_dir = tmp_path / "indexes"
    embedding_ready.mkdir()
    output_dir.mkdir()
    (embedding_ready / "chunks.jsonl").write_text("", encoding="utf-8")
    (embedding_ready / "corpus_manifest.json").write_text(json.dumps({"corpus_id": "SIH26045"}), encoding="utf-8")
    chunk = _chunk("c1", "doc1", "Dataset_1/A.pdf")
    messages = validate_index(
        chunks=[chunk],
        embeddings=[_embedding_for_chunk(chunk)],
        bm25_metadata={"indexed_chunks": 1, "chunk_id_by_position": ["c1"]},
        index_manifest={**_manifest_for_validation(embedding_dimension=4), "source_corpus_manifest_hash": "wrong"},
        output_dir=output_dir,
    )
    assert "SOURCE_CORPUS_MANIFEST_HASH_MISMATCH" in {m.code for m in messages}


def test_validation_checks_all_qdrant_payload_chunk_ids(tmp_path: Path) -> None:
    chunks = [_chunk("c1", "doc1", "Dataset_1/A.pdf")]
    client = _FakeQdrantClient([{"chunk_id": "c1"}, {"chunk_id": "unknown"}])
    messages = validate_index(
        chunks=chunks,
        embeddings=[_embedding_for_chunk(chunks[0])],
        bm25_metadata={"indexed_chunks": 1, "chunk_id_by_position": ["c1"]},
        index_manifest={**_manifest_for_validation(embedding_dimension=4), "qdrant_enabled": True},
        output_dir=tmp_path,
        qdrant_client=client,
    )
    assert "QDRANT_UNKNOWN_CHUNK_ID" in {m.code for m in messages}


def _chunk(chunk_id: str, document_id: str, relative_path: str, text: str = "Section 1. Test content.") -> dict:
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "dataset_id": relative_path.split("/", 1)[0],
        "document_name": Path(relative_path).name,
        "text": text,
        "embedding_text": f"TITLE:\nTest\n\nCONTENT:\n{text}",
        "metadata": {"document_type": "Statute", "jurisdiction": "India", "legal_domains": ["test"]},
        "provenance": {"relative_path": relative_path, "pdf_page_start": 1, "pdf_page_end": 1, "section": "Section 1", "subsection": None, "article": None, "chapter": None},
        "hashes": {"chunk_text_sha256": "text", "source_sha256": "source"},
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _embedding_for_chunk(chunk: dict) -> EmbeddingRecord:
    return EmbeddingRecord(
        chunk_id=chunk["chunk_id"],
        cache_key="k",
        embedding_model="hash-4",
        embedding_provider="deterministic_hash",
        embedding_dimension=4,
        embedding=[0.1, 0.2, 0.3, 0.4],
        embedding_input_sha256=sha256_text(chunk["embedding_text"]),
        normalized=True,
        model_revision="deterministic",
        indexing_version="1.0.0",
    )


def _manifest_for_validation(*, embedding_dimension: int) -> dict:
    return {
        "embedding_dimension": embedding_dimension,
        "embedding_provider": "deterministic_hash",
        "embedding_model": "hash-4",
        "embedding_model_revision": "deterministic",
        "embedding_normalize": True,
        "corpus_id": "SIH26045",
        "qdrant_enabled": False,
    }


class _FakeQdrantClient:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads

    def count(self) -> int:
        return len(self.payloads)

    def iter_payloads(self) -> list[dict]:
        return self.payloads
