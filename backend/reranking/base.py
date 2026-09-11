"""Reranking interfaces and implementations.

Provides:
    Reranker          — Protocol for any reranker
    PassthroughReranker  — No-op (just truncates to top_k)
    CrossEncoderReranker — Real cross-encoder via sentence-transformers
"""

from __future__ import annotations

import logging
from typing import Protocol

from backend.retrieval.models import RetrievedChunk

LOG = logging.getLogger(__name__)


class Reranker(Protocol):
    """Protocol for rerankers."""

    def rerank(self, query: str, candidates: list[RetrievedChunk], top_k: int = 8) -> list[RetrievedChunk]:
        ...


class PassthroughReranker:
    """No-op reranker — returns candidates truncated to top_k.

    Useful for testing and environments where a cross-encoder is unavailable.
    Does NOT provide semantic reranking quality.
    """

    def rerank(self, query: str, candidates: list[RetrievedChunk], top_k: int = 8) -> list[RetrievedChunk]:
        return candidates[:top_k]


class CrossEncoderReranker:
    """Cross-encoder reranker using sentence-transformers.

    Default model: ``cross-encoder/ms-marco-MiniLM-L-6-v2``
    This is a lightweight model suitable for CPU execution.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = "cpu") -> None:
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "CrossEncoderReranker requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            ) from exc
        self.model = CrossEncoder(model_name, device=device)
        self.model_name = model_name
        LOG.info("CrossEncoderReranker loaded: %s on %s", model_name, device)

    def rerank(self, query: str, candidates: list[RetrievedChunk], top_k: int = 8) -> list[RetrievedChunk]:
        if not candidates:
            return []

        pairs = [(query, c.text) for c in candidates]
        scores = self.model.predict(pairs, show_progress_bar=False)

        for candidate, score in zip(candidates, scores):
            candidate.rerank_score = float(score)

        reranked = sorted(candidates, key=lambda c: c.rerank_score or 0.0, reverse=True)
        return reranked[:top_k]


def make_reranker(provider: str = "passthrough", model: str = "", device: str = "cpu") -> Reranker:
    """Factory for reranker instances."""
    if provider in {"cross_encoder", "sentence_transformers"}:
        return CrossEncoderReranker(model_name=model or "cross-encoder/ms-marco-MiniLM-L-6-v2", device=device)
    return PassthroughReranker()
