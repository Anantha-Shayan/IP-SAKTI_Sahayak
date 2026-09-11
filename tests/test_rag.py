"""Tests for RAG module."""

from backend.rag.generation import DummyGenerator, assemble_evidence, RAGPipeline
from backend.reranking.base import DummyReranker
from backend.retrieval.query import SearchResult

class DummyRetriever:
    def search(self, query: str, top_k: int = 10, filters=None):
        return [
            SearchResult(chunk_id="c1", document_id="d1", text="Context text 1", score=0.9, metadata={}),
            SearchResult(chunk_id="c2", document_id="d2", text="Context text 2", score=0.8, metadata={})
        ][:top_k]

def test_assemble_evidence():
    results = [
        SearchResult(chunk_id="c1", document_id="d1", text="Text 1", score=0.9, metadata={}),
        SearchResult(chunk_id="c2", document_id="d2", text="Text 2", score=0.8, metadata={}),
    ]
    context = assemble_evidence(results)
    assert "[Document 1] (ID: d1):\nText 1" in context
    assert "[Document 2] (ID: d2):\nText 2" in context

def test_rag_pipeline():
    retriever = DummyRetriever()
    reranker = DummyReranker()
    generator = DummyGenerator()
    
    pipeline = RAGPipeline(retriever, reranker, generator)
    res = pipeline.answer("test query", top_k_retrieve=2, top_k_rerank=2)
    
    assert "Dummy Answer" in res["answer"]
    assert "Context text 1" in res["context"]
    assert len(res["sources"]) == 2
