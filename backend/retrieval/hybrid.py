"""Hybrid retrieval combining BM25 and dense results via Reciprocal Rank Fusion."""

from __future__ import annotations

import logging
from typing import Any

from .bm25 import BM25Retriever
from .dense import DenseRetriever
from .models import RetrievedChunk

LOG = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]],
    *,
    k: int = 60,
    top_k: int = 40,
) -> list[RetrievedChunk]:
    """Merge multiple ranked lists via RRF.

    ``RRF_score(d) = sum_over_lists(1 / (k + rank_in_list))``

    Preserves per-method scores and ranks from the input results.
    """
    scores: dict[str, float] = {}
    best_chunk: dict[str, RetrievedChunk] = {}

    for results in result_lists:
        for rank_0, rc in enumerate(results):
            rrf_contrib = 1.0 / (k + rank_0 + 1)
            scores[rc.chunk_id] = scores.get(rc.chunk_id, 0.0) + rrf_contrib

            # Keep the version with the richest metadata
            if rc.chunk_id not in best_chunk:
                best_chunk[rc.chunk_id] = rc
            else:
                _merge_scores(best_chunk[rc.chunk_id], rc)

    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]

    merged: list[RetrievedChunk] = []
    for cid in sorted_ids:
        rc = best_chunk[cid]
        rc.hybrid_score = scores[cid]
        rc.score = scores[cid]
        rc.retrieval_method = "hybrid"
        merged.append(rc)

    return merged


def _merge_scores(target: RetrievedChunk, source: RetrievedChunk) -> None:
    """Copy per-method scores from *source* into *target* where missing."""
    if source.bm25_score is not None and target.bm25_score is None:
        target.bm25_score = source.bm25_score
        target.bm25_rank = source.bm25_rank
    if source.dense_score is not None and target.dense_score is None:
        target.dense_score = source.dense_score
        target.dense_rank = source.dense_rank


class HybridRetriever:
    """Runs BM25 + dense retrieval and fuses with RRF."""

    def __init__(
        self,
        bm25: BM25Retriever,
        dense: DenseRetriever,
        *,
        rrf_k: int = 60,
    ) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        *,
        bm25_top_k: int = 30,
        dense_top_k: int = 30,
        hybrid_top_k: int = 40,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Run both retrievers and fuse results."""
        bm25_results = self.bm25.search(query, top_k=bm25_top_k)
        dense_results = self.dense.search(query, top_k=dense_top_k, filters=filters)

        LOG.info(
            "Hybrid search: bm25=%d hits, dense=%d hits",
            len(bm25_results),
            len(dense_results),
        )

        return reciprocal_rank_fusion(
            [bm25_results, dense_results],
            k=self.rrf_k,
            top_k=hybrid_top_k,
        )
