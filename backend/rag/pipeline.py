"""End-to-end RAG pipeline orchestrator.

    TEXT QUERY → Query Processing → Hybrid Retrieval → Reranking → Evidence Pack → LLM → Answer + Citations
"""

from __future__ import annotations

import logging
from typing import Any

from backend.reranking.base import Reranker
from backend.retrieval.config import RetrievalConfig, RerankerConfig, GenerationConfig
from backend.retrieval.hybrid import HybridRetriever
from backend.retrieval.models import RetrievedChunk
from backend.retrieval.query import QueryAnalysis, process_query

from .generation import (
    EvidencePack,
    Generator,
    RAGResponse,
    build_evidence_pack,
)

LOG = logging.getLogger(__name__)


class RAGPipeline:
    """Full text RAG pipeline."""

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: Reranker,
        generator: Generator,
        *,
        retrieval_config: RetrievalConfig | None = None,
        generation_config: GenerationConfig | None = None,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator
        self.retrieval_config = retrieval_config or RetrievalConfig()
        self.generation_config = generation_config or GenerationConfig()

    def retrieve(
        self,
        query: str,
        *,
        bm25_top_k: int | None = None,
        dense_top_k: int | None = None,
        hybrid_top_k: int | None = None,
        reranker_top_k: int | None = None,
    ) -> dict[str, Any]:
        """Run retrieval + reranking without LLM generation.  Useful for evaluation."""
        cfg = self.retrieval_config
        analysis = process_query(query)

        hybrid_results = self.retriever.search(
            analysis.normalized_query,
            bm25_top_k=bm25_top_k or cfg.bm25_top_k,
            dense_top_k=dense_top_k or cfg.dense_top_k,
            hybrid_top_k=hybrid_top_k or cfg.hybrid_top_k,
        )

        # Step 2: Apply exact legal-reference boost
        from backend.retrieval.filters import apply_exact_reference_boost
        boosted_candidates = apply_exact_reference_boost(
            analysis.original_query,
            hybrid_results,
            legal_references=analysis.legal_references,
        )

        reranked = self.reranker.rerank(
            analysis.normalized_query,
            boosted_candidates,
            top_k=reranker_top_k or 8,
        )

        # Re-apply exact reference boost after reranking to preserve statutory priority
        reranked = apply_exact_reference_boost(
            analysis.original_query,
            reranked,
            legal_references=analysis.legal_references,
        )

        return {
            "query_analysis": analysis.to_dict(),
            "hybrid_results": [r.to_dict() for r in hybrid_results],
            "reranked_results": [r.to_dict() for r in reranked],
            "retrieval_stats": {
                "bm25_top_k": bm25_top_k or cfg.bm25_top_k,
                "dense_top_k": dense_top_k or cfg.dense_top_k,
                "hybrid_candidates": len(hybrid_results),
                "reranked_candidates": len(reranked),
            },
        }

    def answer(
        self,
        query: str,
        *,
        bm25_top_k: int | None = None,
        dense_top_k: int | None = None,
        hybrid_top_k: int | None = None,
        reranker_top_k: int | None = None,
    ) -> RAGResponse:
        """Full RAG pipeline: query → retrieval → reranking → evidence → LLM → answer."""
        cfg = self.retrieval_config
        analysis = process_query(query)

        hybrid_results = self.retriever.search(
            analysis.normalized_query,
            bm25_top_k=bm25_top_k or cfg.bm25_top_k,
            dense_top_k=dense_top_k or cfg.dense_top_k,
            hybrid_top_k=hybrid_top_k or cfg.hybrid_top_k,
        )

        # Step 2: Apply exact legal-reference boost
        from backend.retrieval.filters import apply_exact_reference_boost
        boosted_candidates = apply_exact_reference_boost(
            analysis.original_query,
            hybrid_results,
            legal_references=analysis.legal_references,
        )

        reranked = self.reranker.rerank(
            analysis.normalized_query,
            boosted_candidates,
            top_k=reranker_top_k or 8,
        )

        # Re-apply exact reference boost after reranking to preserve statutory priority
        reranked = apply_exact_reference_boost(
            analysis.original_query,
            reranked,
            legal_references=analysis.legal_references,
        )

        evidence_pack = build_evidence_pack(
            query=analysis.original_query,
            normalized_query=analysis.normalized_query,
            reranked=reranked,
        )

        response = self.generator.generate(analysis.normalized_query, evidence_pack)
        response.retrieval_stats = {
            "bm25_top_k": bm25_top_k or cfg.bm25_top_k,
            "dense_top_k": dense_top_k or cfg.dense_top_k,
            "hybrid_candidates": len(hybrid_results),
            "reranked_candidates": len(reranked),
        }

        return response
