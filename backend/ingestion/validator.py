"""Corpus validation and duplicate/collision detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import ValidationMessage


def validate_document(document: dict[str, Any], pages: list[Any], chunks: list[dict[str, Any]]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    rel = document["relative_path"]
    if document["page_count"] != len(pages):
        messages.append(ValidationMessage("CRITICAL", "PAGE_COUNT_MISMATCH", f"{rel}: PDF page count differs from extracted page count.", document["document_id"], rel))
    if [p.page_index for p in pages] != list(range(len(pages))):
        messages.append(ValidationMessage("CRITICAL", "PAGE_SEQUENCE_GAP", f"{rel}: extracted page sequence is not contiguous.", document["document_id"], rel))
    empty = [p for p in pages if not p.text.strip()]
    failed = [p for p in pages if p.extraction_failed]
    if empty:
        messages.append(ValidationMessage("WARNING", "EMPTY_PAGES", f"{rel}: {len(empty)} pages have empty extracted text.", document["document_id"], rel))
    if failed:
        messages.append(ValidationMessage("CRITICAL", "FAILED_PAGES", f"{rel}: {len(failed)} pages failed extraction.", document["document_id"], rel))
    if not chunks and pages:
        messages.append(ValidationMessage("CRITICAL", "NO_CHUNKS", f"{rel}: no chunks generated.", document["document_id"], rel))
    for chunk in chunks:
        tokens = chunk["token_count"]
        if tokens > 900:
            messages.append(ValidationMessage("WARNING", "OVERSIZE_CHUNK", f"{rel}: chunk {chunk['chunk_index']} has {tokens} tokens.", document["document_id"], rel))
    return messages


def apply_duplicate_detection(
    documents: list[dict[str, Any]],
    pages_by_doc: dict[str, list[Any]],
    chunks: list[dict[str, Any]],
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    by_file_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in documents:
        by_file_hash[doc["source_sha256"]].append(doc)
    for docs in by_file_hash.values():
        if len(docs) > 1:
            names = ", ".join(d["relative_path"] for d in docs)
            messages.append(ValidationMessage("WARNING", "DUPLICATE_PDF_FILE", f"Duplicate PDF file hash shared by: {names}"))

    global_pages: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for doc in documents:
        seen: dict[str, list[Any]] = defaultdict(list)
        for page in pages_by_doc[doc["document_id"]]:
            if page.text.strip():
                seen[page.page_text_sha256].append(page)
                global_pages[page.page_text_sha256].append((doc["document_id"], page))
        for same_hash_pages in seen.values():
            if len(same_hash_pages) > 1:
                for page in same_hash_pages:
                    page.duplicate_within_document = True
                messages.append(ValidationMessage("WARNING", "DUPLICATE_PAGE_WITHIN_DOCUMENT", f"{doc['relative_path']}: {len(same_hash_pages)} pages share identical text.", doc["document_id"], doc["relative_path"]))

    for same_hash_pages in global_pages.values():
        doc_ids = {doc_id for doc_id, _ in same_hash_pages}
        if len(doc_ids) > 1:
            for _, page in same_hash_pages:
                page.duplicate_across_documents = True

    for i, left in enumerate(documents):
        left_hashes = {p.page_text_sha256 for p in pages_by_doc[left["document_id"]] if p.text.strip()}
        if not left_hashes:
            continue
        for right in documents[i + 1 :]:
            right_hashes = {p.page_text_sha256 for p in pages_by_doc[right["document_id"]] if p.text.strip()}
            if not right_hashes:
                continue
            overlap = len(left_hashes & right_hashes) / max(1, min(len(left_hashes), len(right_hashes)))
            if overlap >= 0.80:
                messages.append(
                    ValidationMessage(
                        "CRITICAL",
                        "CRITICAL_DOCUMENT_CONTENT_COLLISION",
                        f"{left['relative_path']} and {right['relative_path']} share {overlap:.0%} identical extracted pages.",
                    )
                )

    chunk_hashes: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        chunk_hashes[chunk["hashes"]["chunk_text_sha256"]].append(chunk["chunk_id"])
    dup_chunks = sum(1 for ids in chunk_hashes.values() if len(ids) > 1)
    if dup_chunks:
        messages.append(ValidationMessage("WARNING", "DUPLICATE_CHUNKS", f"{dup_chunks} chunk text hashes are duplicated."))
    return messages


def document_validation_status(messages: list[ValidationMessage]) -> str:
    if any(m.severity == "CRITICAL" for m in messages):
        return "FAILED"
    if any(m.severity == "WARNING" for m in messages):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def corpus_validation_status(messages: list[ValidationMessage]) -> str:
    if any(m.severity == "CRITICAL" for m in messages):
        return "FAILED"
    if any(m.severity == "WARNING" for m in messages):
        return "PASS_WITH_WARNINGS"
    return "PASS"

