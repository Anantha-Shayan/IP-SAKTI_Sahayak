"""Retrieval, reranking, and RAG configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RetrievalConfig:
    bm25_top_k: int = int(os.getenv("RETRIEVAL_BM25_TOP_K", "30"))
    dense_top_k: int = int(os.getenv("RETRIEVAL_DENSE_TOP_K", "30"))
    hybrid_top_k: int = int(os.getenv("RETRIEVAL_HYBRID_TOP_K", "40"))
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    index_dir: Path = Path(os.getenv("INDEX_OUTPUT_DIR", "data/processed/indexes"))
    chunks_path: Path = Path(os.getenv("INDEX_CHUNKS_PATH", "data/processed/embedding_ready/chunks.jsonl"))


@dataclass(frozen=True)
class RerankerConfig:
    provider: str = os.getenv("RERANKER_PROVIDER", "cross_encoder")
    model: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    top_k: int = int(os.getenv("RERANKER_TOP_K", "8"))
    device: str = os.getenv("RERANKER_DEVICE", "cpu")


@dataclass(frozen=True)
class GenerationConfig:
    provider: str = os.getenv("LLM_PROVIDER", "google")
    model: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    api_key: str | None = os.getenv("LLM_API_KEY")
    grounding_min_score: float = float(os.getenv("GROUNDING_MIN_SCORE", "0.15"))
    abstention_message: str = os.getenv(
        "GROUNDING_ABSTENTION_MESSAGE",
        "I could not find sufficient evidence in the indexed corpus to answer this question reliably.",
    )
