"""End-to-end embedding-ready ingestion pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .chunker import build_chunks
from .config import CORPUS_ID, PROCESSOR_VERSION
from .hashing import sha256_file
from .manifest import build_manifest, write_json, write_jsonl, write_validation_reports
from .metadata import build_document_metadata, dataset_id_for, make_document_id
from .models import ValidationMessage
from .models import PageRecord
from .pdf_loader import discover_pdfs, extract_pdf_pages
from .structure_parser import annotate_page_structure, empty_structure, split_structural_blocks
from .validator import apply_duplicate_detection, document_validation_status, validate_document

LOG = logging.getLogger(__name__)


def run_pipeline(
    *,
    input_dir: Path,
    output_dir: Path,
    ocr: bool = False,
    workers: int = 1,
    force: bool = False,
    validate_only: bool = False,
    chunk_size: int = 600,
    chunk_overlap: int = 80,
) -> dict[str, Any]:
    del workers  # reserved for a future process pool; serial keeps PyMuPDF/OCR deterministic.
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = discover_pdfs(input_dir)
    LOG.info("Found %d PDF documents", len(pdfs))

    previous = _load_previous_documents(output_dir)
    documents: list[dict[str, Any]] = []
    pages_by_doc: dict[str, list[Any]] = {}
    all_chunks: list[dict[str, Any]] = []
    messages: list[ValidationMessage] = []

    for pdf in pdfs:
        rel = pdf.relative_to(input_dir).as_posix()
        dataset_id = dataset_id_for(rel)
        source_hash = sha256_file(pdf)
        document_id = make_document_id(dataset_id, rel)
        LOG.info("Processing %s", rel)
        cached = _load_document_cache(output_dir, document_id)
        cache_valid = _cache_valid(cached, source_hash=source_hash, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if cached and cache_valid and not force:
            LOG.info("%s unchanged; reused cached extraction and chunks", rel)
            document = cached["document"]
            pages = [PageRecord(**row) for row in cached["pages"]]
            chunks = cached["chunks"] if not validate_only else []
            messages.extend(ValidationMessage(**row) for row in cached.get("messages", []))
            doc_messages = validate_document(document, pages, chunks)
            messages.extend(doc_messages)
            document["validation_status"] = document_validation_status(doc_messages)
            documents.append(document)
            pages_by_doc[document_id] = pages
            all_chunks.extend(chunks)
            messages.append(ValidationMessage("INFO", "DOCUMENT_PROCESSED", f"{len(pages)} pages extracted from {rel}.", document_id, rel))
            continue

        try:
            pages, page_messages, page_count = extract_pdf_pages(
                pdf_path=pdf,
                document_id=document_id,
                dataset_id=dataset_id,
                ocr_enabled=ocr,
            )
            messages.extend(_with_relative(page_messages, rel))
            first_text = "\n\n".join(p.text for p in pages[:3])
            document = build_document_metadata(
                source_path=pdf,
                raw_root=input_dir,
                source_sha256=source_hash,
                page_count=page_count,
                first_pages_text=first_text,
            )
            context = empty_structure()
            page_dicts: list[dict[str, Any]] = []
            for page in pages:
                page_structure, context = annotate_page_structure(page.text, context)
                page.structure = page_structure
                page_dicts.append(page.to_json())
            blocks = split_structural_blocks(page_dicts)
            chunks = [] if validate_only else build_chunks(document=document, blocks=blocks, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            document["chunk_count"] = len(chunks)
            document["extracted_character_count"] = sum(p.character_count for p in pages)
            document["extracted_word_count"] = sum(p.word_count for p in pages)
            document["usable_text_page_percentage"] = round(100 * sum(1 for p in pages if p.text.strip()) / max(1, len(pages)), 2)
            document["ocr_page_count"] = sum(1 for p in pages if p.ocr_used)
            document["duplicate_page_count"] = 0
            document["suspicious_page_count"] = sum(1 for p in pages if not p.text.strip() or p.extraction_failed)
            doc_messages = validate_document(document, pages, chunks)
            messages.extend(doc_messages)
            document["validation_status"] = document_validation_status(doc_messages)
            _write_document_cache(
                output_dir,
                document_id,
                {
                    "processor_version": PROCESSOR_VERSION,
                    "source_sha256": source_hash,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "document": document,
                    "pages": [p.to_json() for p in pages],
                    "chunks": chunks,
                    "messages": [m.to_json() for m in page_messages],
                },
            )
            documents.append(document)
            pages_by_doc[document_id] = pages
            all_chunks.extend(chunks)
            messages.append(ValidationMessage("INFO", "DOCUMENT_PROCESSED", f"{len(pages)} pages extracted from {rel}.", document_id, rel))
            LOG.info("Extracted %d pages", len(pages))
            LOG.info("Detected %d OCR pages", document["ocr_page_count"])
            LOG.info("Generated %d chunks", len(chunks))
        except Exception as exc:
            messages.append(ValidationMessage("CRITICAL", "DOCUMENT_PROCESSING_FAILED", f"{rel}: {exc}", document_id, rel))
            documents.append(
                {
                    "processor_version": PROCESSOR_VERSION,
                    "document_id": document_id,
                    "corpus_id": CORPUS_ID,
                    "dataset_id": dataset_id,
                    "dataset_description": None,
                    "filename": pdf.name,
                    "relative_path": rel,
                    "title": None,
                    "document_type": "Other",
                    "jurisdiction": None,
                    "authority": None,
                    "language": None,
                    "legal_domains": [],
                    "publication_date": None,
                    "effective_date": None,
                    "source_sha256": source_hash,
                    "page_count": 0,
                    "chunk_count": 0,
                    "ocr_page_count": 0,
                    "validation_status": "FAILED",
                    "failure_reason": str(exc),
                }
            )
            pages_by_doc[document_id] = []
            LOG.critical("Failed processing %s: %s", rel, exc)

    messages.extend(apply_duplicate_detection(documents, pages_by_doc, all_chunks))
    for doc in documents:
        doc_pages = pages_by_doc.get(doc["document_id"], [])
        doc["duplicate_page_count"] = sum(1 for p in doc_pages if p.duplicate_within_document or p.duplicate_across_documents)
        related = [m for m in messages if m.document_id == doc["document_id"]]
        if doc.get("validation_status") != "FAILED":
            doc["validation_status"] = document_validation_status(related)

    page_rows = [p.to_json() for doc in documents for p in pages_by_doc.get(doc["document_id"], [])]
    manifest = build_manifest(documents, len(page_rows), all_chunks, messages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    LOG.info("Writing embedding-ready dataset")
    if not validate_only:
        write_jsonl(output_dir / "chunks.jsonl", all_chunks)
    write_json(output_dir / "documents.json", documents)
    write_jsonl(output_dir / "pages.jsonl", page_rows)
    write_json(output_dir / "corpus_manifest.json", manifest)
    write_validation_reports(output_dir, messages, documents)
    return {"manifest": manifest, "messages": [m.to_json() for m in messages], "documents": documents, "chunks": all_chunks}


def _load_previous_documents(output_dir: Path) -> dict[str, dict[str, Any]]:
    path = output_dir / "documents.json"
    if not path.exists():
        return {}


def _cache_path(output_dir: Path, document_id: str) -> Path:
    return output_dir / ".cache" / f"{document_id}.json"


def _load_document_cache(output_dir: Path, document_id: str) -> dict[str, Any] | None:
    path = _cache_path(output_dir, document_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_valid(cached: dict[str, Any] | None, *, source_hash: str, chunk_size: int, chunk_overlap: int) -> bool:
    return bool(
        cached
        and cached.get("processor_version") == PROCESSOR_VERSION
        and cached.get("source_sha256") == source_hash
        and cached.get("chunk_size") == chunk_size
        and cached.get("chunk_overlap") == chunk_overlap
    )


def _write_document_cache(output_dir: Path, document_id: str, data: dict[str, Any]) -> None:
    path = _cache_path(output_dir, document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        docs = json.loads(path.read_text(encoding="utf-8"))
        return {doc["document_id"]: doc for doc in docs}
    except Exception:
        return {}


def _with_relative(messages: list[ValidationMessage], relative_path: str) -> list[ValidationMessage]:
    for message in messages:
        if message.relative_path and "/" not in message.relative_path:
            message.relative_path = relative_path
    return messages
