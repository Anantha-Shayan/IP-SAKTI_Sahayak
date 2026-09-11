"""Tests for RAG module — unit tests using dummy/mock components."""

from backend.rag.generation import (
    DummyGenerator,
    GeminiGenerator,
    build_evidence_pack,
    RAGResponse,
)
from backend.rag.pipeline import RAGPipeline
from backend.reranking.base import PassthroughReranker
from backend.retrieval.models import RetrievedChunk


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
    """Mimics HybridRetriever.search() for testing."""

    def __init__(self, results: list[RetrievedChunk] | None = None):
        self._results = [
            _make_chunk("c1", "Bio_Diversity_Act.pdf", "The Biological Diversity Act provides..."),
            _make_chunk("c2", "Patents_Act.pdf", "Patent applications must comply with..."),
        ] if results is None else results

    def search(self, query, *, bm25_top_k=30, dense_top_k=30, hybrid_top_k=40, filters=None):
        return self._results[:hybrid_top_k]


# ---------------------------------------------------------------------------
# Evidence / Citation building
# ---------------------------------------------------------------------------


def test_build_evidence_pack():
    chunks = [
        _make_chunk("c1", "Bio_Diversity_Act.pdf", "Text 1"),
        _make_chunk("c2", "Patents_Act.pdf", "Text 2"),
    ]
    pack = build_evidence_pack("test query", "test query", chunks)
    assert len(pack.chunks) == 2
    assert len(pack.citations) == 2
    assert pack.chunks[0].citation_id == "[1]"
    assert pack.chunks[1].citation_id == "[2]"
    assert pack.citations[0].document_name == "Bio_Diversity_Act.pdf"


# ---------------------------------------------------------------------------
# Dummy generator
# ---------------------------------------------------------------------------


def test_dummy_generator_with_evidence():
    gen = DummyGenerator()
    chunks = [_make_chunk("c1", "test.pdf", "Evidence text")]
    pack = build_evidence_pack("q", "q", chunks)
    response = gen.generate("q", pack)
    assert response.answer
    assert len(response.citations) == 1
    assert response.grounded is True


def test_dummy_generator_no_evidence():
    gen = DummyGenerator()
    pack = build_evidence_pack("q", "q", [])
    response = gen.generate("q", pack)
    assert "No evidence" in response.answer or "sufficient evidence" in response.answer
    assert response.grounded is False


# ---------------------------------------------------------------------------
# RAG Pipeline end-to-end (with mocks)
# ---------------------------------------------------------------------------


def test_rag_pipeline():
    retriever = DummyHybridRetriever()
    reranker = PassthroughReranker()
    generator = DummyGenerator()

    pipeline = RAGPipeline(retriever, reranker, generator)
    response = pipeline.answer("test query")

    assert isinstance(response, RAGResponse)
    assert response.answer
    assert len(response.citations) == 2
    assert len(response.evidence) == 2
    assert response.grounded is True


def test_rag_pipeline_retrieve_only():
    retriever = DummyHybridRetriever()
    reranker = PassthroughReranker()
    generator = DummyGenerator()

    pipeline = RAGPipeline(retriever, reranker, generator)
    result = pipeline.retrieve("test query")

    assert "query_analysis" in result
    assert "hybrid_results" in result
    assert "reranked_results" in result
    assert len(result["reranked_results"]) == 2


def test_rag_pipeline_no_results():
    retriever = DummyHybridRetriever(results=[])
    reranker = PassthroughReranker()
    generator = DummyGenerator()

    pipeline = RAGPipeline(retriever, reranker, generator)
    response = pipeline.answer("something obscure")

    # With no retrieval results, the dummy generator should indicate no evidence
    assert response.grounded is False or "No evidence" in response.answer


def test_rag_pipeline_abstention():
    """GeminiGenerator without API key should abstain when no evidence is found."""
    retriever = DummyHybridRetriever(results=[])
    reranker = PassthroughReranker()
    generator = GeminiGenerator(api_key="")  # No key → falls back to dummy internally

    pipeline = RAGPipeline(retriever, reranker, generator)
    response = pipeline.answer("What is quantum computing?")

    # With no evidence, Gemini generator should abstain (returns its abstention message)
    assert response.grounded is False or "insufficient" in response.answer.lower() or "No evidence" in response.answer
