"""BM25 retriever operating on the persisted BM25 index.

Uses the same tokenizer (``tokenize_legal_text``) and configuration that was
used during indexing so that legal references remain searchable.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.indexing.bm25_index import tokenize_legal_text
from backend.indexing.config import BM25Config

from .models import RetrievedChunk

LOG = logging.getLogger(__name__)


class BM25Retriever:
    """Loads the persisted BM25 index and scores queries against it."""

    def __init__(self, index_dir: Path, chunks_path: Path, config: BM25Config | None = None) -> None:
        if config is None:
            config = BM25Config()
        self.config = config

        index_file = index_dir / "bm25" / "index" / "bm25_index.json"
        if not index_file.exists():
            raise FileNotFoundError(f"BM25 index not found: {index_file}")
        with open(index_file, "r", encoding="utf-8") as fh:
            index_data = json.load(fh)

        self.metadata = index_data["metadata"]
        self.document_lengths: list[int] = index_data["document_lengths"]
        self.term_frequencies: list[dict[str, int]] = index_data["term_frequencies"]
        self.idf: dict[str, float] = index_data["idf"]

        self.chunk_ids: list[str] = self.metadata["chunk_id_by_position"]
        self.avgdl: float = self.metadata["average_document_length"]
        self.n_docs: int = self.metadata["indexed_chunks"]

        self.k1: float = self.metadata["bm25"]["k1"]
        self.b: float = self.metadata["bm25"]["b"]

        # Load full chunk data for provenance
        self._chunks_by_id: dict[str, dict[str, Any]] = {}
        if chunks_path.exists():
            with open(chunks_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        chunk = json.loads(line)
                        self._chunks_by_id[chunk["chunk_id"]] = chunk

        LOG.info("BM25Retriever loaded: %d docs, %d terms", self.n_docs, len(self.idf))

    def search(self, query: str, top_k: int = 30) -> list[RetrievedChunk]:
        """Score *query* against the BM25 index and return top-k results."""
        query_tokens = tokenize_legal_text(query, self.config)
        if not query_tokens:
            return []

        scores = [0.0] * self.n_docs
        for token in query_tokens:
            token_idf = self.idf.get(token)
            if token_idf is None:
                continue
            for doc_idx, term_freq in enumerate(self.term_frequencies):
                freq = term_freq.get(token, 0)
                if freq == 0:
                    continue
                doc_len = self.document_lengths[doc_idx]
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                scores[doc_idx] += token_idf * (numerator / denominator)

        top_indices = sorted(range(self.n_docs), key=lambda i: scores[i], reverse=True)[:top_k]

        results: list[RetrievedChunk] = []
        for rank, idx in enumerate(top_indices):
            if scores[idx] <= 0.0:
                break
            chunk_id = self.chunk_ids[idx]
            chunk = self._chunks_by_id.get(chunk_id, {})
            rc = RetrievedChunk.from_chunk_dict(
                chunk if chunk else {"chunk_id": chunk_id, "document_id": "", "text": ""},
                score=scores[idx],
                retrieval_method="bm25",
            )
            rc.bm25_score = scores[idx]
            rc.bm25_rank = rank + 1
            results.append(rc)

        return results
