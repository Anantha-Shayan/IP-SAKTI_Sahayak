"""Pure-Python BM25 index builder and persistence."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .config import BM25Config, INDEXING_VERSION
from .io import write_json

LEGAL_TOKEN_RE = re.compile(
    r"\b(?:section|article|rule|regulation)\s+\d+[a-z]?(?:\(\w+\))*|\b\d+[a-z]?(?:\(\w+\))+|\b[a-zA-Z][a-zA-Z0-9_-]*\b|\b\d+[a-zA-Z]?\b",
    re.IGNORECASE,
)

DEFAULT_STOPWORDS = {
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "by",
    "with",
    "as",
    "on",
    "is",
    "are",
}


def tokenize_legal_text(text: str, config: BM25Config) -> list[str]:
    tokens = [m.group(0) for m in LEGAL_TOKEN_RE.finditer(text)]
    if config.lowercase:
        tokens = [t.lower() for t in tokens]
    if config.remove_stopwords:
        tokens = [t for t in tokens if t not in DEFAULT_STOPWORDS]
    return tokens


def build_bm25(chunks: list[dict[str, Any]], config: BM25Config, output_dir: Path) -> dict[str, Any]:
    tokenized = [tokenize_legal_text(chunk["text"], config) for chunk in chunks]
    doc_freq: dict[str, int] = defaultdict(int)
    term_freqs: list[dict[str, int]] = []
    lengths: list[int] = []
    for tokens in tokenized:
        counts = Counter(tokens)
        term_freqs.append(dict(counts))
        lengths.append(len(tokens))
        for term in counts:
            doc_freq[term] += 1
    n_docs = len(chunks)
    avgdl = sum(lengths) / n_docs if n_docs else 0.0
    idf = {term: math.log(1 + (n_docs - df + 0.5) / (df + 0.5)) for term, df in sorted(doc_freq.items())}
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    metadata = {
        "indexing_version": INDEXING_VERSION,
        "bm25": {
            "k1": config.k1,
            "b": config.b,
            "lowercase": config.lowercase,
            "remove_stopwords": config.remove_stopwords,
            "tokenizer_version": config.tokenizer_version,
        },
        "indexed_chunks": n_docs,
        "average_document_length": avgdl,
        "chunk_id_by_position": chunk_ids,
    }
    index = {
        "metadata": metadata,
        "document_lengths": lengths,
        "term_frequencies": term_freqs,
        "idf": idf,
    }
    bm25_dir = output_dir / "bm25"
    write_json(bm25_dir / "index" / "bm25_index.json", index)
    write_json(bm25_dir / "metadata.json", metadata)
    return metadata

