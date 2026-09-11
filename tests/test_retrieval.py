"""Tests for retrieval module — unit tests that work without external services."""

import pytest
from backend.retrieval.models import RetrievedChunk
from backend.retrieval.hybrid import reciprocal_rank_fusion
from backend.retrieval.query import (
    process_query,
    extract_legal_references,
    normalize_whitespace,
)


# ---------------------------------------------------------------------------
# Query processing
# ---------------------------------------------------------------------------


def test_normalize_whitespace():
    assert normalize_whitespace("  hello   world  ") == "hello world"


def test_extract_legal_references():
    refs = extract_legal_references("See Section 3(1)(a) and Article 5 of the Act")
    assert any("Section 3(1)(a)" in r for r in refs)
    assert any("Article 5" in r for r in refs)


def test_process_query_preserves_legal_refs():
    analysis = process_query("What does Section 3(1)(a) of the Biological Diversity Act say?")
    assert analysis.normalized_query
    assert len(analysis.legal_references) >= 1
    assert analysis.detected_domain == "biodiversity"


def test_process_query_trademark():
    analysis = process_query("How to register a trademark under the Trade Marks Act?")
    assert analysis.detected_domain == "intellectual property"


# ---------------------------------------------------------------------------
# Reciprocal rank fusion
# ---------------------------------------------------------------------------


def _make_chunk(chunk_id: str, doc_id: str, score: float, method: str = "bm25") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_name=f"doc_{doc_id}",
        dataset_id="test",
        text=f"Text for {chunk_id}",
        score=score,
        retrieval_method=method,
    )


def test_reciprocal_rank_fusion():
    list1 = [
        _make_chunk("c1", "d1", 0.9, "bm25"),
        _make_chunk("c2", "d2", 0.8, "bm25"),
    ]
    list2 = [
        _make_chunk("c2", "d2", 0.85, "dense"),
        _make_chunk("c3", "d3", 0.7, "dense"),
    ]

    results = reciprocal_rank_fusion([list1, list2], k=60, top_k=3)

    assert len(results) == 3
    # c2 appears in both lists → highest RRF score
    assert results[0].chunk_id == "c2"
    assert results[1].chunk_id == "c1"
    assert results[2].chunk_id == "c3"
    # all should be tagged hybrid
    assert all(r.retrieval_method == "hybrid" for r in results)


def test_rrf_empty_lists():
    results = reciprocal_rank_fusion([], k=60, top_k=5)
    assert results == []


def test_rrf_single_list():
    single = [_make_chunk("c1", "d1", 0.9)]
    results = reciprocal_rank_fusion([single], k=60, top_k=5)
    assert len(results) == 1
    assert results[0].chunk_id == "c1"


def test_exact_reference_boost():
    from backend.retrieval.filters import apply_exact_reference_boost
    c1 = RetrievedChunk(
        chunk_id="c1", document_id="d1", document_name="TK_Examination_Guidelines.pdf",
        dataset_id="test", text="General discussion on patents", score=0.03, retrieval_method="hybrid"
    )
    c2 = RetrievedChunk(
        chunk_id="c2", document_id="d2", document_name="Biological_Diversity_Amendment_Act_2023.pdf",
        dataset_id="test", text="Section 3(1)(a) details certain restrictions", score=0.03, retrieval_method="hybrid"
    )
    boosted = apply_exact_reference_boost("What does Section 3(1)(a) of the Biological Diversity Act say?", [c1, c2])
    # c2 matches both the exact reference 'Section 3(1)(a)' and the target Act
    assert boosted[0].chunk_id == "c2"
    assert boosted[0].score > boosted[1].score
