"""Tests for retrieval module."""

import pytest
from backend.retrieval.query import SearchResult
from backend.retrieval.hybrid import reciprocal_rank_fusion

def test_reciprocal_rank_fusion():
    list1 = [
        SearchResult(chunk_id="c1", document_id="d1", text="text1", score=0.9, metadata={}),
        SearchResult(chunk_id="c2", document_id="d2", text="text2", score=0.8, metadata={}),
    ]
    list2 = [
        SearchResult(chunk_id="c2", document_id="d2", text="text2", score=0.85, metadata={}),
        SearchResult(chunk_id="c3", document_id="d3", text="text3", score=0.7, metadata={}),
    ]
    
    results = reciprocal_rank_fusion([list1, list2], k=60, top_k=3)
    
    assert len(results) == 3
    # c2 is at rank 1 in list1 (0-indexed) -> 1/(60+2) = 1/62
    # c2 is at rank 0 in list2 -> 1/(60+1) = 1/61
    # total score for c2 = 1/62 + 1/61 ~ 0.0325
    # c1 is at rank 0 in list1 -> 1/61 ~ 0.0163
    # c3 is at rank 1 in list2 -> 1/62 ~ 0.0161
    # Order should be c2, c1, c3
    assert results[0].chunk_id == "c2"
    assert results[1].chunk_id == "c1"
    assert results[2].chunk_id == "c3"
