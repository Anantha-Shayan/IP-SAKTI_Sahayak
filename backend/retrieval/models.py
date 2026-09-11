"""Retrieval data models preserving full provenance for citations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedChunk:
    """A chunk returned from any retrieval method, with full provenance."""

    chunk_id: str
    document_id: str
    document_name: str
    dataset_id: str
    text: str
    score: float
    retrieval_method: str  # "bm25", "dense", "hybrid"

    # Provenance — everything needed for citations
    source_path: str | None = None
    pdf_page_start: int | None = None
    pdf_page_end: int | None = None
    printed_page_start: int | None = None
    printed_page_end: int | None = None
    section: str | None = None
    subsection: str | None = None
    article: str | None = None
    chapter: str | None = None
    rule: str | None = None
    regulation: str | None = None

    # Document metadata
    document_type: str | None = None
    jurisdiction: str | None = None
    legal_domains: list[str] = field(default_factory=list)

    # Per-method scores for hybrid results
    bm25_score: float | None = None
    bm25_rank: int | None = None
    dense_score: float | None = None
    dense_rank: int | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None

    # Collision metadata
    content_collision: bool = False
    collision_group_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_chunk_dict(cls, chunk: dict[str, Any], *, score: float, retrieval_method: str) -> RetrievedChunk:
        """Build from a raw chunk dict (as loaded from chunks.jsonl)."""
        prov = chunk.get("provenance", {})
        meta = chunk.get("metadata", {})
        indexing = chunk.get("indexing", {})
        return cls(
            chunk_id=chunk["chunk_id"],
            document_id=chunk["document_id"],
            document_name=chunk.get("document_name", ""),
            dataset_id=chunk.get("dataset_id", ""),
            text=chunk.get("text", ""),
            score=score,
            retrieval_method=retrieval_method,
            source_path=prov.get("relative_path"),
            pdf_page_start=prov.get("pdf_page_start"),
            pdf_page_end=prov.get("pdf_page_end"),
            printed_page_start=prov.get("printed_page_start"),
            printed_page_end=prov.get("printed_page_end"),
            section=prov.get("section") or meta.get("section"),
            subsection=prov.get("subsection"),
            article=prov.get("article") or meta.get("article"),
            chapter=prov.get("chapter"),
            rule=prov.get("rule"),
            regulation=prov.get("regulation"),
            document_type=meta.get("document_type"),
            jurisdiction=meta.get("jurisdiction"),
            legal_domains=meta.get("legal_domains", []),
            content_collision=indexing.get("content_collision", False),
            collision_group_id=indexing.get("collision_group_id"),
        )

    @classmethod
    def from_qdrant_payload(cls, payload: dict[str, Any], *, score: float) -> RetrievedChunk:
        """Build from a Qdrant point payload."""
        prov = payload.get("provenance", {})
        return cls(
            chunk_id=payload.get("chunk_id", ""),
            document_id=payload.get("document_id", ""),
            document_name=payload.get("document_name", ""),
            dataset_id=payload.get("dataset_id", ""),
            text=payload.get("text", ""),
            score=score,
            retrieval_method="dense",
            source_path=payload.get("source_path"),
            pdf_page_start=payload.get("page_start"),
            pdf_page_end=payload.get("page_end"),
            printed_page_start=payload.get("printed_page_start"),
            printed_page_end=payload.get("printed_page_end"),
            section=payload.get("section") or prov.get("section"),
            subsection=prov.get("subsection"),
            article=payload.get("article") or prov.get("article"),
            chapter=payload.get("chapter") or prov.get("chapter"),
            rule=prov.get("rule"),
            regulation=prov.get("regulation"),
            document_type=payload.get("document_type"),
            jurisdiction=payload.get("jurisdiction"),
            legal_domains=payload.get("legal_domains", []),
            content_collision=payload.get("content_collision", False),
            collision_group_id=payload.get("collision_group_id"),
            dense_score=score,
        )
