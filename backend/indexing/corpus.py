"""Load embedding-ready chunks and derive corpus-side indexing metadata."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from backend.ingestion.hashing import sha256_text

from .io import read_json, read_jsonl


def source_manifest_hash(chunks_path: Path) -> str:
    manifest = chunks_path.parent / "corpus_manifest.json"
    if manifest.exists():
        return sha256_text(manifest.read_text(encoding="utf-8"))
    return sha256_text("missing-corpus-manifest")


def load_documents(chunks_path: Path) -> list[dict[str, Any]]:
    docs_path = chunks_path.parent / "documents.json"
    return read_json(docs_path) if docs_path.exists() else []


def load_corpus_manifest(chunks_path: Path) -> dict[str, Any] | None:
    path = chunks_path.parent / "corpus_manifest.json"
    return read_json(path) if path.exists() else None


def load_collision_groups(chunks_path: Path) -> dict[str, dict[str, Any]]:
    report_path = chunks_path.parent / "validation_report.json"
    if not report_path.exists():
        return {}
    report = read_json(report_path)
    collisions: dict[str, dict[str, Any]] = {}
    group_index = 0
    for message in report.get("messages", []):
        if message.get("code") != "CRITICAL_DOCUMENT_CONTENT_COLLISION":
            continue
        paths = re.findall(r"Dataset_[\w]+/[^\s]+?\.pdf|Dataset_[\w]+/[^\s]+?\.PDF", message.get("message", ""))
        if len(paths) < 2:
            continue
        group_id = sha256_text("collision", group_index, *sorted(paths))
        for rel in paths:
            collisions[rel] = {
                "content_collision": True,
                "collision_group_id": group_id,
                "collision_message": message.get("message"),
            }
        group_index += 1
    return collisions


def eligible_chunks(chunks_path: Path, *, index_collision_documents: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    collisions = load_collision_groups(chunks_path)
    indexed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for chunk in read_jsonl(chunks_path):
        chunk.pop("_source_line", None)
        rel = chunk.get("provenance", {}).get("relative_path")
        collision = collisions.get(rel)
        if collision:
            chunk["indexing"] = collision
        else:
            chunk["indexing"] = {"content_collision": False, "collision_group_id": None}
        if collision and not index_collision_documents:
            skipped.append({"chunk_id": chunk["chunk_id"], "document_id": chunk["document_id"], "reason": "content_collision", "relative_path": rel})
            continue
        if not chunk.get("text", "").strip() or not chunk.get("embedding_text", "").strip():
            skipped.append({"chunk_id": chunk.get("chunk_id"), "document_id": chunk.get("document_id"), "reason": "empty_text_or_embedding_text", "relative_path": rel})
            continue
        indexed.append(chunk)
    return indexed, skipped, collisions


def skipped_documents(documents: list[dict[str, Any]], indexed_chunks: list[dict[str, Any]], skipped_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed_doc_ids = {chunk["document_id"] for chunk in indexed_chunks}
    skipped_by_doc: dict[str, list[str]] = defaultdict(list)
    for chunk in skipped_chunks:
        if chunk.get("document_id"):
            skipped_by_doc[chunk["document_id"]].append(chunk["reason"])
    result: list[dict[str, Any]] = []
    for doc in documents:
        if doc["document_id"] not in indexed_doc_ids:
            reason = "zero_chunks" if doc.get("chunk_count", 0) == 0 else ",".join(sorted(set(skipped_by_doc.get(doc["document_id"], ["not_indexed"]))))
            result.append({"document_id": doc["document_id"], "relative_path": doc["relative_path"], "reason": reason, "chunk_count": doc.get("chunk_count", 0)})
    return result

