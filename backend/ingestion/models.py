"""Typed records used by the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageRecord:
    processor_version: str
    corpus_id: str
    document_id: str
    page_id: str
    dataset_id: str
    page_index: int
    pdf_page_number: int
    printed_page_number: int | None
    text: str
    raw_text: str
    character_count: int
    word_count: int
    ocr_used: bool
    extraction_method: str
    extraction_failed: bool
    failure_reason: str | None
    page_text_sha256: str
    duplicate_within_document: bool = False
    duplicate_across_documents: bool = False
    structure: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ValidationMessage:
    severity: str
    code: str
    message: str
    document_id: str | None = None
    relative_path: str | None = None
    page_index: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

