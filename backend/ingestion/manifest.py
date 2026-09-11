"""Manifest and report writers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import CORPUS_ID, PROCESSOR_VERSION
from .validator import corpus_validation_status


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_manifest(
    documents: list[dict[str, Any]],
    pages_total: int,
    chunks: list[dict[str, Any]],
    messages: list[Any],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> dict[str, Any]:
    return {
        "processor_version": PROCESSOR_VERSION,
        "corpus_id": CORPUS_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunking_strategy": "legal-structure-paragraph-sentence-token",
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "documents_total": len(documents),
        "pages_total": pages_total,
        "chunks_total": len(chunks),
        "documents_successful": sum(1 for d in documents if d.get("validation_status") != "FAILED"),
        "documents_failed": sum(1 for d in documents if d.get("validation_status") == "FAILED"),
        "ocr_pages": sum(d.get("ocr_page_count", 0) for d in documents),
        "warnings": sum(1 for m in messages if m.severity == "WARNING"),
        "critical_errors": sum(1 for m in messages if m.severity == "CRITICAL"),
        "validation_status": corpus_validation_status(messages),
        "documents": [
            {
                "document_id": d["document_id"],
                "filename": d["filename"],
                "relative_path": d["relative_path"],
                "dataset_id": d["dataset_id"],
                "page_count": d["page_count"],
                "chunk_count": d.get("chunk_count", 0),
                "source_sha256": d["source_sha256"],
                "validation_status": d.get("validation_status"),
            }
            for d in documents
        ],
    }


def write_validation_reports(output_dir: Path, messages: list[Any], documents: list[dict[str, Any]]) -> None:
    data = {
        "processor_version": PROCESSOR_VERSION,
        "corpus_id": CORPUS_ID,
        "validation_status": corpus_validation_status(messages),
        "counts": {
            "critical": sum(1 for m in messages if m.severity == "CRITICAL"),
            "warning": sum(1 for m in messages if m.severity == "WARNING"),
            "info": sum(1 for m in messages if m.severity == "INFO"),
        },
        "documents": documents,
        "messages": [m.to_json() for m in messages],
    }
    write_json(output_dir / "validation_report.json", data)
    lines = [
        f"Validation status: {data['validation_status']}",
        f"CRITICAL: {data['counts']['critical']}",
        f"WARNING: {data['counts']['warning']}",
        f"INFO: {data['counts']['info']}",
        "",
    ]
    for severity in ["CRITICAL", "WARNING", "INFO"]:
        selected = [m for m in messages if m.severity == severity]
        if selected:
            lines.append(f"{severity}:")
            lines.extend(f"- [{m.code}] {m.message}" for m in selected)
            lines.append("")
    (output_dir / "validation_report.txt").write_text("\n".join(lines), encoding="utf-8")

