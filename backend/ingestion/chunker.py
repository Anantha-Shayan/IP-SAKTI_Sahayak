"""Structure-aware semantic chunking."""

from __future__ import annotations

import re
from typing import Any

from .config import CORPUS_ID, PROCESSOR_VERSION
from .hashing import sha256_text


def count_tokens(text: str) -> int:
    return len(re.findall(r"\S+", text))


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=(?:[A-Z0-9(]))", text)
    return [p.strip() for p in parts if p.strip()]


def split_large_text(text: str, target_tokens: int) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for para in paras or [text]:
        if count_tokens(para) <= target_tokens:
            units.append(para)
        else:
            units.extend(split_sentences(para))
    split_units: list[str] = []
    for unit in units:
        if count_tokens(unit) <= target_tokens:
            split_units.append(unit)
            continue
        words = re.findall(r"\S+", unit)
        for start in range(0, len(words), target_tokens):
            split_units.append(" ".join(words[start : start + target_tokens]))
    return split_units


def overlap_tail(text: str, overlap_tokens: int) -> str:
    if overlap_tokens <= 0:
        return ""
    sentences = split_sentences(text)
    selected: list[str] = []
    total = 0
    for sent in reversed(sentences or [text]):
        tokens = count_tokens(sent)
        if tokens > overlap_tokens:
            words = re.findall(r"\S+", sent)
            selected.insert(0, " ".join(words[-overlap_tokens:]))
            break
        if selected and total + tokens > overlap_tokens:
            break
        selected.insert(0, sent)
        total += tokens
        if total >= overlap_tokens:
            break
    if not selected:
        words = re.findall(r"\S+", text)
        return " ".join(words[-overlap_tokens:])
    return " ".join(selected)


def make_embedding_text(document: dict[str, Any], structure: dict[str, Any], text: str) -> str:
    fields = [
        ("TITLE", document.get("title")),
        ("DOCUMENT TYPE", document.get("document_type")),
        ("JURISDICTION", document.get("jurisdiction")),
        ("PART", structure.get("part")),
        ("CHAPTER", structure.get("chapter")),
        ("SCHEDULE", structure.get("schedule")),
        ("SECTION", structure.get("section")),
        ("ARTICLE", structure.get("article")),
        ("RULE", structure.get("rule")),
        ("REGULATION", structure.get("regulation")),
        ("CASE", structure.get("case_name")),
        ("CONTENT", text),
    ]
    return "\n\n".join(f"{label}:\n{value}" for label, value in fields if value)


def build_chunks(
    *,
    document: dict[str, Any],
    blocks: list[dict[str, Any]],
    chunk_size: int = 600,
    chunk_overlap: int = 80,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    sequence = 0
    active_text = ""
    active_meta: dict[str, Any] | None = None

    def emit(text: str, meta: dict[str, Any]) -> None:
        nonlocal sequence
        text = text.strip()
        if not text:
            return
        text_hash = sha256_text(text)
        chunk_id = sha256_text(document["document_id"], meta["page_start"], meta["page_end"], sequence, text_hash)
        structure = meta["structure"]
        provenance = {
            "source_file": document["filename"],
            "relative_path": document["relative_path"],
            "document_id": document["document_id"],
            "page_id": sha256_text(document["document_id"], meta["page_start"] - 1),
            "pdf_page_start": meta["page_start"],
            "pdf_page_end": meta["page_end"],
            "printed_page_start": meta.get("printed_page_start"),
            "printed_page_end": meta.get("printed_page_end"),
            "part": structure.get("part"),
            "chapter": structure.get("chapter"),
            "sub_chapter": structure.get("sub_chapter"),
            "section": structure.get("section"),
            "subsection": structure.get("subsection"),
            "clause": structure.get("clause"),
            "sub_clause": structure.get("sub_clause"),
            "proviso": structure.get("proviso"),
            "explanation": structure.get("explanation"),
            "schedule": structure.get("schedule"),
            "article": structure.get("article"),
            "rule": structure.get("rule"),
            "regulation": structure.get("regulation"),
            "case_name": structure.get("case_name"),
            "court": structure.get("court"),
            "case_number": structure.get("case_number"),
        }
        chunks.append(
            {
                "processor_version": PROCESSOR_VERSION,
                "corpus_id": CORPUS_ID,
                "chunk_id": chunk_id,
                "document_id": document["document_id"],
                "page_id": provenance["page_id"],
                "dataset_id": document["dataset_id"],
                "document_name": document["filename"],
                "chunk_index": sequence,
                "text": text,
                "embedding_text": make_embedding_text(document, structure, text),
                "token_count": count_tokens(text),
                "character_count": len(text),
                "provenance": provenance,
                "metadata": {
                    "document_type": document.get("document_type"),
                    "jurisdiction": document.get("jurisdiction"),
                    "authority": document.get("authority"),
                    "language": document.get("language"),
                    "legal_domains": document.get("legal_domains", []),
                    "dataset_id": document["dataset_id"],
                    "document_id": document["document_id"],
                    "section": structure.get("section"),
                    "article": structure.get("article"),
                    "chapter": structure.get("chapter"),
                    "case_name": structure.get("case_name"),
                },
                "hashes": {
                    "source_sha256": document["source_sha256"],
                    "chunk_text_sha256": text_hash,
                },
            }
        )
        sequence += 1

    for block in blocks:
        block_tokens = count_tokens(block["text"])
        if block_tokens > max(chunk_size * 1.35, 800):
            units = split_large_text(block["text"], chunk_size)
        else:
            units = [block["text"]]

        for unit in units:
            unit_tokens = count_tokens(unit)
            if not active_text:
                active_text = unit
                active_meta = block.copy()
            elif count_tokens(active_text) + unit_tokens <= chunk_size + chunk_overlap:
                active_text += "\n\n" + unit
                active_meta["page_end"] = block["page_end"]
                active_meta["printed_page_end"] = block.get("printed_page_end")
            else:
                emit(active_text, active_meta)
                prefix = overlap_tail(active_text, chunk_overlap)
                active_text = f"{prefix}\n\n{unit}".strip() if prefix else unit
                active_meta = block.copy()
    if active_text and active_meta:
        emit(active_text, active_meta)
    return chunks
