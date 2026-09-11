"""Tests for API module — uses TestClient with mocked pipeline."""

import pytest
from fastapi.testclient import TestClient

from backend.retrieval.models import RetrievedChunk
from backend.rag.generation import DummyGenerator, RAGResponse
from backend.rag.pipeline import RAGPipeline
from backend.reranking.base import PassthroughReranker


def _make_chunk(chunk_id: str, doc_name: str, text: str, score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=f"doc_{chunk_id}",
        document_name=doc_name,
        dataset_id="test",
        text=text,
        score=score,
        retrieval_method="hybrid",
        source_path=f"Dataset_1/{doc_name}",
        pdf_page_start=1,
        pdf_page_end=2,
        section="Section 3",
    )


class DummyHybridRetriever:
    def search(self, query, *, bm25_top_k=30, dense_top_k=30, hybrid_top_k=40, filters=None):
        return [
            _make_chunk("c1", "Bio_Diversity_Act.pdf", "The Act provides for conservation of biodiversity"),
            _make_chunk("c2", "Patents_Act.pdf", "Patent applications must be filed with the Controller"),
        ][:hybrid_top_k]


@pytest.fixture
def client():
    """Create a test client with a mocked pipeline (no external services)."""
    import backend.api.main as api_module

    # Inject pipeline directly
    retriever = DummyHybridRetriever()
    reranker = PassthroughReranker()
    generator = DummyGenerator()
    api_module._pipeline = RAGPipeline(retriever, reranker, generator)
    api_module._init_errors = []
    api_module._mode_info = {"bm25": "mock", "dense": "mock", "reranker": "passthrough", "generator": "dummy"}

    return TestClient(api_module.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_query(client):
    response = client.post("/api/query", json={"query": "What does the Biological Diversity Act say?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert "evidence" in data
    assert len(data["citations"]) >= 1


def test_api_retrieve(client):
    response = client.post("/api/retrieve", json={"query": "patent application"})
    assert response.status_code == 200
    data = response.json()
    assert "query_analysis" in data
    assert "reranked_results" in data
    assert len(data["reranked_results"]) >= 1


def test_api_query_empty(client):
    """Even an odd query should not crash."""
    response = client.post("/api/query", json={"query": "xyzzy foobar nonsense"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
