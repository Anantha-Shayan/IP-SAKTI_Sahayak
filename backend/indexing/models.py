"""Shared indexing records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationMessage:
    severity: str
    code: str
    message: str
    chunk_id: str | None = None
    document_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class EmbeddingRecord:
    chunk_id: str
    cache_key: str
    embedding_model: str
    embedding_provider: str
    embedding_dimension: int
    embedding: list[float]
    embedding_input_sha256: str
    normalized: bool
    model_revision: str | None
    indexing_version: str

    def to_json(self) -> dict[str, Any]:
        return self.__dict__.copy()

