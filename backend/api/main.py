"""FastAPI application for IP-SAKTI Sahayak.

Provides two main endpoints:
    POST /api/query    — Full RAG: retrieval → reranking → LLM → grounded answer + citations
    POST /api/retrieve — Retrieval + reranking only (no LLM), useful for debugging

Startup bootstraps real components where available, falls back to mocks otherwise.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── project imports ──────────────────────────────────────────────────────────
from backend.retrieval.config import RetrievalConfig, RerankerConfig, GenerationConfig
from backend.retrieval.models import RetrievedChunk
from backend.rag.pipeline import RAGPipeline
from backend.rag.generation import (
    GeminiGenerator,
    GroqGenerator,
    DummyGenerator,
    RAGResponse,
)
from backend.reranking.base import make_reranker

LOG = logging.getLogger(__name__)

# ── request/response models ─────────────────────────────────────────────────


class QueryRequest(BaseModel):
    query: str
    top_k_retrieve: int = Field(default=20, ge=1, le=100)
    top_k_rerank: int = Field(default=8, ge=1, le=50)


class RetrieveRequest(BaseModel):
    query: str
    bm25_top_k: int = Field(default=30, ge=1, le=100)
    dense_top_k: int = Field(default=30, ge=1, le=100)
    hybrid_top_k: int = Field(default=40, ge=1, le=100)
    reranker_top_k: int = Field(default=8, ge=1, le=50)


# ── global pipeline instance ────────────────────────────────────────────────
_pipeline: RAGPipeline | None = None
_init_errors: list[str] = []
_mode_info: dict[str, str] = {}


def _build_pipeline() -> tuple[RAGPipeline | None, list[str], dict[str, str]]:
    """Construct the RAG pipeline, recording what succeeded and what fell back."""
    errors: list[str] = []
    mode: dict[str, str] = {}
    ret_cfg = RetrievalConfig()
    rer_cfg = RerankerConfig()
    gen_cfg = GenerationConfig()

    # ── BM25 ─────────────────────────────────────────────────────────────
    bm25 = None
    try:
        from backend.retrieval.bm25 import BM25Retriever
        bm25 = BM25Retriever(ret_cfg.index_dir, ret_cfg.chunks_path)
        mode["bm25"] = "real"
        LOG.info("BM25 retriever loaded (%d docs)", bm25.n_docs)
    except Exception as exc:
        errors.append(f"BM25 init failed: {exc}")
        LOG.warning("BM25 init failed: %s", exc)

    # ── Dense / Qdrant ───────────────────────────────────────────────────
    dense = None
    try:
        from backend.retrieval.dense import DenseRetriever
        dense = DenseRetriever()
        # Quick health check
        from backend.indexing.qdrant_index import QdrantRestClient
        from backend.indexing.config import QdrantConfig
        QdrantRestClient(QdrantConfig()).healthcheck()
        mode["dense"] = "real"
        LOG.info("Dense retriever loaded (Qdrant)")
    except Exception as exc:
        errors.append(f"Dense/Qdrant init failed: {exc}")
        LOG.warning("Dense/Qdrant init failed: %s", exc)

    # ── Hybrid ───────────────────────────────────────────────────────────
    hybrid = None
    if bm25 and dense:
        from backend.retrieval.hybrid import HybridRetriever
        hybrid = HybridRetriever(bm25, dense, rrf_k=ret_cfg.rrf_k)
        mode["hybrid"] = "real"
    elif bm25:
        # BM25-only fallback — wrap to match HybridRetriever.search signature
        hybrid = _BM25OnlyHybrid(bm25)
        mode["hybrid"] = "bm25_only"
        LOG.warning("Hybrid using BM25 only (Qdrant unavailable)")
    elif dense:
        hybrid = _DenseOnlyHybrid(dense)
        mode["hybrid"] = "dense_only"
        LOG.warning("Hybrid using Dense only (BM25 unavailable)")
    else:
        errors.append("Neither BM25 nor Dense retriever available — cannot build pipeline")
        return None, errors, mode

    # ── Reranker ─────────────────────────────────────────────────────────
    try:
        reranker = make_reranker(rer_cfg.provider, rer_cfg.model, rer_cfg.device)
        mode["reranker"] = rer_cfg.provider
        LOG.info("Reranker: %s", rer_cfg.provider)
    except Exception as exc:
        from backend.reranking.base import PassthroughReranker
        reranker = PassthroughReranker()
        mode["reranker"] = "passthrough"
        errors.append(f"Reranker fallback to passthrough: {exc}")
        LOG.warning("Reranker fallback: %s", exc)

    # ── Generator ────────────────────────────────────────────────────────
    provider = (gen_cfg.provider or "").strip().lower()
    # prefer explicit config api_key, then common env vars, then provider-specific
    api_key = gen_cfg.api_key or os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")

    if provider in ("google", "gemini", "g"):
        if api_key:
            generator = GeminiGenerator(
                model=gen_cfg.model,
                api_key=api_key,
                temperature=gen_cfg.temperature,
                max_tokens=gen_cfg.max_tokens,
                grounding_min_score=gen_cfg.grounding_min_score,
                abstention_message=gen_cfg.abstention_message,
            )
            mode["generator"] = f"gemini/{gen_cfg.model}"
        else:
            generator = DummyGenerator(
                grounding_min_score=gen_cfg.grounding_min_score,
                abstention_message=gen_cfg.abstention_message,
            )
            mode["generator"] = "dummy (no LLM_API_KEY)"
            errors.append("No LLM API key — using dummy generator")
    elif provider in ("groq", "groqai"):
        if api_key:
            generator = GroqGenerator(
                model=gen_cfg.model,
                api_key=api_key,
                temperature=gen_cfg.temperature,
                max_tokens=gen_cfg.max_tokens,
                grounding_min_score=gen_cfg.grounding_min_score,
                abstention_message=gen_cfg.abstention_message,
            )
            mode["generator"] = f"groq/{gen_cfg.model}"
        else:
            generator = DummyGenerator(
                grounding_min_score=gen_cfg.grounding_min_score,
                abstention_message=gen_cfg.abstention_message,
            )
            mode["generator"] = "dummy (no GROQ_API_KEY)"
            errors.append("No GROQ API key — using dummy generator")
    else:
        # default behavior: try Gemini first, otherwise dummy
        if api_key:
            generator = GeminiGenerator(
                model=gen_cfg.model,
                api_key=api_key,
                temperature=gen_cfg.temperature,
                max_tokens=gen_cfg.max_tokens,
                grounding_min_score=gen_cfg.grounding_min_score,
                abstention_message=gen_cfg.abstention_message,
            )
            mode["generator"] = f"gemini/{gen_cfg.model}"
        else:
            generator = DummyGenerator(
                grounding_min_score=gen_cfg.grounding_min_score,
                abstention_message=gen_cfg.abstention_message,
            )
            mode["generator"] = "dummy (no LLM_API_KEY)"
            errors.append("No LLM API key — using dummy generator")

    pipeline = RAGPipeline(
        retriever=hybrid,
        reranker=reranker,
        generator=generator,
        retrieval_config=ret_cfg,
        generation_config=gen_cfg,
    )
    return pipeline, errors, mode


# ── Fallback wrappers for single-retriever mode ─────────────────────────────


class _BM25OnlyHybrid:
    """Wraps a BM25Retriever to match HybridRetriever.search() signature."""

    def __init__(self, bm25):
        self.bm25 = bm25

    def search(self, query, *, bm25_top_k=30, dense_top_k=30, hybrid_top_k=40, filters=None):
        results = self.bm25.search(query, top_k=bm25_top_k)
        for r in results:
            r.hybrid_score = r.bm25_score
            r.retrieval_method = "hybrid"
        return results[:hybrid_top_k]


class _DenseOnlyHybrid:
    """Wraps a DenseRetriever to match HybridRetriever.search() signature."""

    def __init__(self, dense):
        self.dense = dense

    def search(self, query, *, bm25_top_k=30, dense_top_k=30, hybrid_top_k=40, filters=None):
        results = self.dense.search(query, top_k=dense_top_k, filters=filters)
        for r in results:
            r.hybrid_score = r.dense_score
            r.retrieval_method = "hybrid"
        return results[:hybrid_top_k]


# ── app factory ──────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title="IP-SAKTI Sahayak",
        description="RAG-based legal assistant for Indian IP & Traditional Knowledge law",
        version="0.1.0-demo",
    )

    cors_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup():
        global _pipeline, _init_errors, _mode_info
        _pipeline, _init_errors, _mode_info = _build_pipeline()
        if _pipeline:
            LOG.info("Pipeline ready. Modes: %s", _mode_info)
        else:
            LOG.error("Pipeline FAILED to initialize: %s", _init_errors)
        if _init_errors:
            LOG.warning("Init warnings: %s", _init_errors)

    # ── endpoints ────────────────────────────────────────────────────────

    @app.get("/health")
    def health():
        return {
            "status": "ok" if _pipeline else "degraded",
            "modes": _mode_info,
            "errors": _init_errors,
        }

    @app.post("/api/query")
    def api_query(req: QueryRequest):
        if not _pipeline:
            raise HTTPException(500, detail=f"Pipeline not available: {_init_errors}")
        try:
            response: RAGResponse = _pipeline.answer(
                req.query,
                hybrid_top_k=req.top_k_retrieve,
                reranker_top_k=req.top_k_rerank,
            )
            return response.to_dict()
        except Exception as exc:
            LOG.error("Query failed: %s\n%s", exc, traceback.format_exc())
            raise HTTPException(500, detail=str(exc))

    @app.post("/api/retrieve")
    def api_retrieve(req: RetrieveRequest):
        if not _pipeline:
            raise HTTPException(500, detail=f"Pipeline not available: {_init_errors}")
        try:
            result = _pipeline.retrieve(
                req.query,
                bm25_top_k=req.bm25_top_k,
                dense_top_k=req.dense_top_k,
                hybrid_top_k=req.hybrid_top_k,
                reranker_top_k=req.reranker_top_k,
            )
            return result
        except Exception as exc:
            LOG.error("Retrieve failed: %s\n%s", exc, traceback.format_exc())
            raise HTTPException(500, detail=str(exc))

    return app


# ── CLI entry point ──────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Load .env if present (lightweight, no extra dependency)
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    LOG.info("Starting IP-SAKTI Sahayak on %s:%d", host, port)
    uvicorn.run("backend.api.main:app", host=host, port=port, reload=False)
