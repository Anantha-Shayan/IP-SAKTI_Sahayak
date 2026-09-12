"""Evidence assembly, citation generation, and grounded LLM generation.

Design principles:
    - The LLM is NOT the source of truth; the corpus and retrieved evidence are.
    - ABSTENTION > HALLUCINATION.
    - Citations must come from actual chunk provenance, never guessed.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.retrieval.models import RetrievedChunk

LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evidence / Citation models
# ---------------------------------------------------------------------------


@dataclass
class Citation:
    """A citation pointing back to a specific source chunk."""

    citation_id: str          # e.g. "[1]"
    chunk_id: str
    document_name: str
    source_path: str | None
    pdf_page_start: int | None
    pdf_page_end: int | None
    printed_page_start: int | None = None
    printed_page_end: int | None = None
    section: str | None = None
    article: str | None = None
    chapter: str | None = None
    rule: str | None = None
    regulation: str | None = None
    document_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class EvidenceChunk:
    """A single evidence chunk selected for LLM generation."""

    chunk_id: str
    text: str
    document_name: str
    citation_id: str
    rerank_score: float | None = None
    hybrid_score: float | None = None
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    article: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class EvidencePack:
    """The complete evidence package passed to the LLM."""

    query: str
    normalized_query: str
    chunks: list[EvidenceChunk] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "chunks": [c.to_dict() for c in self.chunks],
            "citations": [c.to_dict() for c in self.citations],
        }


def build_evidence_pack(
    query: str,
    normalized_query: str,
    reranked: list[RetrievedChunk],
) -> EvidencePack:
    """Build an EvidencePack with deterministic citation IDs from reranked results."""
    pack = EvidencePack(query=query, normalized_query=normalized_query)

    for i, rc in enumerate(reranked):
        cid = f"[{i + 1}]"

        pack.chunks.append(EvidenceChunk(
            chunk_id=rc.chunk_id,
            text=rc.text,
            document_name=rc.document_name,
            citation_id=cid,
            rerank_score=rc.rerank_score,
            hybrid_score=rc.hybrid_score,
            page_start=rc.pdf_page_start,
            page_end=rc.pdf_page_end,
            section=rc.section,
            article=rc.article,
        ))

        pack.citations.append(Citation(
            citation_id=cid,
            chunk_id=rc.chunk_id,
            document_name=rc.document_name,
            source_path=rc.source_path,
            pdf_page_start=rc.pdf_page_start,
            pdf_page_end=rc.pdf_page_end,
            printed_page_start=rc.printed_page_start,
            printed_page_end=rc.printed_page_end,
            section=rc.section,
            article=rc.article,
            chapter=rc.chapter,
            rule=rc.rule,
            regulation=rc.regulation,
            document_type=rc.document_type,
        ))

    return pack


# ---------------------------------------------------------------------------
# Answer schema
# ---------------------------------------------------------------------------


@dataclass
class RAGResponse:
    """Structured response from the RAG pipeline."""

    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = "unknown"
    grounded: bool = True
    retrieval_stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": self.citations,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "grounded": self.grounded,
            "retrieval_stats": self.retrieval_stats,
        }


# ---------------------------------------------------------------------------
# Generator protocol + implementations
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a legal research assistant for Indian intellectual property and traditional knowledge law.

STRICT RULES:
1. Answer ONLY from the supplied evidence documents below.
2. Do NOT invent statutes, sections, cases, dates, authorities, or facts.
3. Do NOT fabricate citations or references.
4. Cite claims using the supplied citation IDs (e.g. [1], [2]).
5. Never cite a document that was not supplied as evidence.
6. Never manufacture page numbers or legal provisions.
7. If the evidence is insufficient to answer, explicitly say so.
8. Distinguish between directly supported statements and reasonable synthesis.
9. Prefer a conservative, accurate answer over a fluent but hallucinated one.
10. If evidence chunks are contradictory, note the contradiction."""


def _build_user_prompt(query: str, evidence_pack: EvidencePack) -> str:
    parts = [f"QUESTION: {query}\n\nEVIDENCE DOCUMENTS:\n"]
    for chunk in evidence_pack.chunks:
        header = f"{chunk.citation_id} {chunk.document_name}"
        if chunk.section:
            header += f" — {chunk.section}"
        if chunk.page_start is not None:
            header += f" (p.{chunk.page_start}"
            if chunk.page_end and chunk.page_end != chunk.page_start:
                header += f"-{chunk.page_end}"
            header += ")"
        parts.append(f"--- {header} ---\n{chunk.text}\n")

    parts.append(
        "\nProvide a grounded answer citing the evidence using the citation IDs. "
        "If the evidence is insufficient, say so explicitly."
    )
    return "\n".join(parts)


class Generator(Protocol):
    """Protocol for LLM generation backends."""

    def generate(self, query: str, evidence_pack: EvidencePack) -> RAGResponse:
        ...


class DummyGenerator:
    """Passthrough generator for testing — does NOT provide real answers."""

    def __init__(self, abstention_message: str = "", grounding_min_score: float = 0.15) -> None:
        self.abstention_message = (
            abstention_message
            or "I could not find sufficient evidence in the indexed corpus to answer this question reliably."
        )
        self.grounding_min_score = grounding_min_score

    def generate(self, query: str, evidence_pack: EvidencePack) -> RAGResponse:
        if not evidence_pack.chunks:
            return RAGResponse(
                answer=self.abstention_message,
                confidence="none",
                grounded=False,
            )

        top_score = max(
            (c.rerank_score for c in evidence_pack.chunks if c.rerank_score is not None),
            default=None,
        )
        if top_score is not None and top_score < self.grounding_min_score:
            return RAGResponse(
                answer=self.abstention_message,
                confidence="low",
                grounded=False,
                citations=[c.to_dict() for c in evidence_pack.citations],
                evidence=[c.to_dict() for c in evidence_pack.chunks],
            )

        # Just echo evidence summaries
        summary_parts = []
        for chunk in evidence_pack.chunks:
            summary_parts.append(f"Based on {chunk.document_name} {chunk.citation_id}: {chunk.text[:200]}...")
        return RAGResponse(
            answer="\n".join(summary_parts),
            citations=[c.to_dict() for c in evidence_pack.citations],
            evidence=[c.to_dict() for c in evidence_pack.chunks],
            confidence="dummy",
            grounded=True,
        )


class GeminiGenerator:
    """Google Gemini API generator."""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        grounding_min_score: float = 0.15,
        abstention_message: str = "",
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.grounding_min_score = grounding_min_score
        self.abstention_message = (
            abstention_message
            or "I could not find sufficient evidence in the indexed corpus to answer this question reliably."
        )

    def generate(self, query: str, evidence_pack: EvidencePack) -> RAGResponse:
        # Abstention: if no evidence or all scores below threshold
        if not evidence_pack.chunks:
            return RAGResponse(
                answer=self.abstention_message,
                confidence="none",
                grounded=False,
                citations=[c.to_dict() for c in evidence_pack.citations],
                evidence=[c.to_dict() for c in evidence_pack.chunks],
            )

        # Check if evidence is above threshold
        top_score = max(
            (c.rerank_score for c in evidence_pack.chunks if c.rerank_score is not None),
            default=None,
        )
        if top_score is not None and top_score < self.grounding_min_score:
            return RAGResponse(
                answer=self.abstention_message,
                confidence="low",
                grounded=False,
                citations=[c.to_dict() for c in evidence_pack.citations],
                evidence=[c.to_dict() for c in evidence_pack.chunks],
            )

        user_prompt = _build_user_prompt(query, evidence_pack)

        if not self.api_key:
            LOG.warning("No LLM_API_KEY set — falling back to dummy generation")
            return DummyGenerator(self.abstention_message).generate(query, evidence_pack)

        try:
            answer_text = self._call_gemini(user_prompt)
        except Exception as exc:
            LOG.error("Gemini API call failed: %s", exc)
            return RAGResponse(
                answer=f"LLM generation failed: {exc}",
                confidence="error",
                grounded=False,
                citations=[c.to_dict() for c in evidence_pack.citations],
                evidence=[c.to_dict() for c in evidence_pack.chunks],
            )

        return RAGResponse(
            answer=answer_text,
            citations=[c.to_dict() for c in evidence_pack.citations],
            evidence=[c.to_dict() for c in evidence_pack.chunks],
            confidence="high" if (top_score and top_score > 0.5) else "medium",
            grounded=True,
        )

    def _call_gemini(self, user_prompt: str) -> str:
        """Call the Gemini REST API."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}"
            f":generateContent?key={self.api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts)
        return "No response generated."


class GroqGenerator:
    """Minimal Groq API generator wrapper.

    This implementation uses a configurable `GROQ_API_URL` (or a sensible
    default) and an API key provided via `GROQ_API_KEY` or `LLM_API_KEY`.
    The request/response JSON shape may need adjustment to match the
    production Groq API; keep this as a reasonable starting point.
    """

    def __init__(
        self,
        model: str = "groq-large",
        api_key: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        grounding_min_score: float = 0.15,
        abstention_message: str = "",
    ) -> None:
        self.model = model
        # Prefer explicit key, then generic LLM_API_KEY, then GROQ_API_KEY
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or ""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.grounding_min_score = grounding_min_score
        self.abstention_message = (
            abstention_message
            or "I could not find sufficient evidence in the indexed corpus to answer this question reliably."
        )

    def generate(self, query: str, evidence_pack: EvidencePack) -> RAGResponse:
        if not evidence_pack.chunks:
            return RAGResponse(answer=self.abstention_message, confidence="none", grounded=False)

        top_score = max(
            (c.rerank_score for c in evidence_pack.chunks if c.rerank_score is not None),
            default=None,
        )
        if top_score is not None and top_score < self.grounding_min_score:
            return RAGResponse(
                answer=self.abstention_message,
                confidence="low",
                grounded=False,
                citations=[c.to_dict() for c in evidence_pack.citations],
                evidence=[c.to_dict() for c in evidence_pack.chunks],
            )

        if not self.api_key:
            LOG.warning("No GROQ API key set — falling back to dummy generation")
            return DummyGenerator(self.abstention_message).generate(query, evidence_pack)

        user_prompt = _build_user_prompt(query, evidence_pack)
        try:
            answer_text = self._call_groq(user_prompt)
        except Exception as exc:
            LOG.error("Groq API call failed: %s", exc)
            return RAGResponse(
                answer=f"LLM generation failed: {exc}",
                confidence="error",
                grounded=False,
                citations=[c.to_dict() for c in evidence_pack.citations],
                evidence=[c.to_dict() for c in evidence_pack.chunks],
            )

        return RAGResponse(
            answer=answer_text,
            citations=[c.to_dict() for c in evidence_pack.citations],
            evidence=[c.to_dict() for c in evidence_pack.chunks],
            confidence="high" if (top_score and top_score > 0.5) else "medium",
            grounded=True,
        )

    def _call_groq(self, user_prompt: str) -> str:
        """Call the Groq Chat Completions REST endpoint (api.groq.com)."""
        base = os.getenv("GROQ_API_URL")
        # If no URL or pointing to old/invalid api.groq.ai domain, use official OpenAI-compatible endpoint
        if not base or "api.groq.ai" in base:
            base = "https://api.groq.com/openai/v1/chat/completions"

        # Determine target model name
        target_model = self.model
        if not target_model or target_model in ("groq-large", "default", "gemini-2.0-flash"):
            target_model = "llama-3.3-70b-versatile"

        # OpenAI Chat Completions payload compatible with Groq
        body = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "IP-SAKTI-Sahayak/1.0",
        }
        req = urllib.request.Request(base, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        # Extract answer from response
        if isinstance(result, dict):
            # Standard OpenAI chat completions format: choices[0].message.content
            choices = result.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message")
                    if isinstance(msg, dict) and "content" in msg:
                        return msg["content"]
                    if "text" in first and isinstance(first["text"], str):
                        return first["text"]

            for key in ("output", "data", "result"):
                if key in result:
                    val = result[key]
                    if isinstance(val, str):
                        return val
                    if isinstance(val, list) and val and isinstance(val[0], str):
                        return val[0]
        return "No response generated."
