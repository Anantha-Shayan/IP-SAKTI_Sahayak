from __future__ import annotations

import json
from pathlib import Path

from backend.ingestion.chunker import build_chunks, count_tokens
from backend.ingestion.config import CORPUS_ID, PROCESSOR_VERSION
from backend.ingestion.hashing import sha256_text
from backend.ingestion.manifest import build_manifest, write_jsonl
from backend.ingestion.metadata import make_document_id
from backend.ingestion.models import PageRecord, ValidationMessage
from backend.ingestion.structure_parser import annotate_page_structure, empty_structure, split_structural_blocks
from backend.ingestion.text_cleaner import clean_page_text
from backend.ingestion.validator import apply_duplicate_detection


def sample_document() -> dict:
    document_id = make_document_id("Dataset_1", "Dataset_1/Test.pdf")
    return {
        "processor_version": PROCESSOR_VERSION,
        "document_id": document_id,
        "corpus_id": CORPUS_ID,
        "dataset_id": "Dataset_1",
        "filename": "Test.pdf",
        "relative_path": "Dataset_1/Test.pdf",
        "title": "The Test Act, 2026",
        "document_type": "Statute",
        "jurisdiction": "India",
        "authority": "Government of India",
        "language": "en",
        "legal_domains": ["test law"],
        "source_sha256": "sourcehash",
        "page_count": 2,
    }


def test_deterministic_document_ids() -> None:
    left = make_document_id("Dataset_1", "Dataset_1/Test.pdf")
    right = make_document_id("Dataset_1", "Dataset_1/Test.pdf")
    other = make_document_id("Dataset_2", "Dataset_2/Test.pdf")
    assert left == right
    assert left != other


def test_deterministic_page_ids() -> None:
    doc_id = make_document_id("Dataset_1", "Dataset_1/Test.pdf")
    assert sha256_text(doc_id, 0) == sha256_text(doc_id, 0)
    assert sha256_text(doc_id, 0) != sha256_text(doc_id, 1)


def test_deterministic_chunk_ids() -> None:
    document = sample_document()
    blocks = [{"text": "Section 1. " + "word " * 80, "page_start": 1, "page_end": 1, "printed_page_start": 1, "printed_page_end": 1, "structure": empty_structure() | {"section": "Section 1"}}]
    assert build_chunks(document=document, blocks=blocks)[0]["chunk_id"] == build_chunks(document=document, blocks=blocks)[0]["chunk_id"]


def test_text_cleaning_preserves_legal_meaning_and_removes_artifacts() -> None:
    raw = "THE TEST ACT\n\nPage 1\n\nbiologi-\ncal resources shall vest in the authority.\n\n\n"
    cleaned = clean_page_text(raw, {"THE TEST ACT"})
    assert "THE TEST ACT" not in cleaned
    assert "Page 1" not in cleaned
    assert "biological resources shall vest" in cleaned


def test_legal_section_detection() -> None:
    first, final = annotate_page_structure("CHAPTER I\nPreliminary\n\n2. Definitions.\n(1) In this Act...\n(a) clause text", empty_structure())
    assert first["chapter"] == "CHAPTER I"
    assert final["section"] == "Section 2"
    assert final["subsection"] == "(1)"
    assert final["clause"] == "(a)"


def test_chunk_size_and_overlap() -> None:
    document = sample_document()
    block_text = "\n\n".join(f"Sentence {i}. " + "word " * 35 for i in range(40))
    blocks = [{"text": block_text, "page_start": 1, "page_end": 2, "printed_page_start": 1, "printed_page_end": 2, "structure": empty_structure() | {"section": "Section 7"}}]
    chunks = build_chunks(document=document, blocks=blocks, chunk_size=120, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(chunk["token_count"] <= 220 for chunk in chunks)
    first_tail = set(chunks[0]["text"].split()[-20:])
    second_head = set(chunks[1]["text"].split()[:30])
    assert first_tail & second_head


def test_page_provenance_in_chunk() -> None:
    document = sample_document()
    blocks = [{"text": "Section 3. Rights and obligations. " + "word " * 50, "page_start": 2, "page_end": 3, "printed_page_start": 10, "printed_page_end": 11, "structure": empty_structure() | {"section": "Section 3"}}]
    chunk = build_chunks(document=document, blocks=blocks)[0]
    assert chunk["provenance"]["pdf_page_start"] == 2
    assert chunk["provenance"]["pdf_page_end"] == 3
    assert chunk["provenance"]["printed_page_start"] == 10
    assert chunk["provenance"]["section"] == "Section 3"


def test_duplicate_and_collision_detection() -> None:
    doc1 = sample_document()
    doc2 = sample_document() | {"document_id": make_document_id("Dataset_1", "Dataset_1/Other.pdf"), "relative_path": "Dataset_1/Other.pdf", "filename": "Other.pdf"}
    pages1 = [_page(doc1, i, f"text {i}") for i in range(5)]
    pages2 = [_page(doc2, i, f"text {i}") for i in range(5)]
    messages = apply_duplicate_detection([doc1, doc2], {doc1["document_id"]: pages1, doc2["document_id"]: pages2}, [])
    assert any(m.code == "CRITICAL_DOCUMENT_CONTENT_COLLISION" for m in messages)
    assert all(p.duplicate_across_documents for p in pages1)


def test_jsonl_validity(tmp_path: Path) -> None:
    path = tmp_path / "chunks.jsonl"
    write_jsonl(path, [{"a": 1}, {"b": "two"}])
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows == [{"a": 1}, {"b": "two"}]


def test_manifest_generation() -> None:
    document = sample_document() | {"chunk_count": 1, "ocr_page_count": 0, "validation_status": "PASS"}
    manifest = build_manifest([document], 2, [{"chunk_id": "c"}], [ValidationMessage("INFO", "OK", "done")], chunk_size=600, chunk_overlap=80)
    assert manifest["corpus_id"] == CORPUS_ID
    assert manifest["documents_total"] == 1
    assert manifest["chunks_total"] == 1
    assert manifest["validation_status"] == "PASS"


def test_structural_blocks_preserve_context() -> None:
    page = {"pdf_page_number": 1, "printed_page_number": 1, "text": "CHAPTER II\n\nSection 7. Access to biological resources.\n\nProvided that prior approval is required."}
    blocks = split_structural_blocks([page])
    assert blocks[0]["structure"]["chapter"] == "CHAPTER II"
    assert blocks[1]["structure"]["section"] == "Section 7"
    assert blocks[1]["structure"]["proviso"] == "Provided that"


def _page(document: dict, index: int, text: str) -> PageRecord:
    return PageRecord(
        processor_version=PROCESSOR_VERSION,
        corpus_id=CORPUS_ID,
        document_id=document["document_id"],
        page_id=sha256_text(document["document_id"], index),
        dataset_id=document["dataset_id"],
        page_index=index,
        pdf_page_number=index + 1,
        printed_page_number=index + 1,
        text=text,
        raw_text=text,
        character_count=len(text),
        word_count=count_tokens(text),
        ocr_used=False,
        extraction_method="fixture",
        extraction_failed=False,
        failure_reason=None,
        page_text_sha256=sha256_text(text),
    )
