"""Tests for API module."""

from fastapi.testclient import TestClient
from backend.api.main import create_app, router
import backend.api.main as api_main
from backend.retrieval.query import SearchResult
from backend.rag.generation import RAGPipeline, DummyGenerator
from backend.reranking.base import DummyReranker

app = create_app()
client = TestClient(app)

class DummyRetriever:
    def search(self, query: str, top_k: int = 10, filters=None):
        return [
            SearchResult(chunk_id="c1", document_id="d1", text="Test Result 1", score=0.9, metadata={})
        ]

def setup_module():
    api_main.retriever = DummyRetriever()
    api_main.rag_pipeline = RAGPipeline(DummyRetriever(), DummyReranker(), DummyGenerator())

def test_search_endpoint():
    response = client.post("/search", json={"query": "test", "top_k": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["chunk_id"] == "c1"

def test_rag_endpoint():
    response = client.post("/rag", json={"query": "test query", "top_k_retrieve": 5, "top_k_rerank": 2})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "context" in data
    assert "sources" in data
    assert "Dummy Answer" in data["answer"]
