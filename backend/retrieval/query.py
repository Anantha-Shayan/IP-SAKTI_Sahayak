"""Query processing: normalization, legal reference detection, and filter inference.

Operates purely on text — no LLM calls for basic normalization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Legal reference patterns
# ---------------------------------------------------------------------------

# "Section 3(1)(a)", "Section 12", "Sec. 5A"
_SECTION_RE = re.compile(
    r"\b(?:section|sec\.?)\s+\d+[a-z]?(?:\(\w+\))*",
    re.IGNORECASE,
)

# "Article 5", "Art. 12(3)"
_ARTICLE_RE = re.compile(
    r"\b(?:article|art\.?)\s+\d+[a-z]?(?:\(\w+\))*",
    re.IGNORECASE,
)

# "Rule 12", "Regulation 4"
_RULE_RE = re.compile(
    r"\b(?:rule|regulation|reg\.?)\s+\d+[a-z]?(?:\(\w+\))*",
    re.IGNORECASE,
)

# "Chapter IV", "Chapter 3"
_CHAPTER_RE = re.compile(
    r"\b(?:chapter)\s+(?:\d+|[IVXLCDM]+)",
    re.IGNORECASE,
)

# Known document-type keywords
_DOC_TYPE_KEYWORDS: dict[str, str] = {
    "act": "Statute",
    "statute": "Statute",
    "rule": "Rule",
    "rules": "Rule",
    "regulation": "Regulation",
    "regulations": "Regulation",
    "notification": "Notification",
    "treaty": "Treaty",
    "protocol": "Protocol",
    "convention": "Convention",
    "manual": "Manual",
    "guideline": "Guideline",
    "guidelines": "Guideline",
    "case": "Case Study",
    "judgement": "Case Study",
    "judgment": "Case Study",
    "order": "Order",
    "circular": "Circular",
}

# Known domain keywords
_DOMAIN_KEYWORDS: dict[str, str] = {
    "patent": "intellectual property",
    "patents": "intellectual property",
    "trademark": "intellectual property",
    "trade mark": "intellectual property",
    "copyright": "intellectual property",
    "design": "intellectual property",
    "biodiversity": "biodiversity",
    "biological diversity": "biodiversity",
    "traditional knowledge": "traditional knowledge",
    "geographical indication": "intellectual property",
    "plant variety": "plant variety",
    "nagoya": "international law",
    "trips": "international law",
    "wipo": "international law",
    "paris convention": "international law",
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class QueryAnalysis:
    """Result of analysing a raw user query."""

    original_query: str
    normalized_query: str
    legal_references: list[str] = field(default_factory=list)
    detected_domain: str | None = None
    detected_document_type: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "legal_references": self.legal_references,
            "detected_domain": self.detected_domain,
            "detected_document_type": self.detected_document_type,
            "filters": self.filters,
        }


# ---------------------------------------------------------------------------
# Processing functions
# ---------------------------------------------------------------------------


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()


def extract_legal_references(text: str) -> list[str]:
    """Extract legal references like 'Section 3(1)(a)', 'Article 5', 'Rule 12'."""
    refs: list[str] = []
    for pattern in (_SECTION_RE, _ARTICLE_RE, _RULE_RE, _CHAPTER_RE):
        for match in pattern.finditer(text):
            ref = normalize_whitespace(match.group(0))
            if ref not in refs:
                refs.append(ref)
    return refs


def detect_document_type(text: str) -> str | None:
    """Detect document type from keywords in the query."""
    lower = text.lower()
    for keyword, doc_type in _DOC_TYPE_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lower):
            return doc_type
    return None


def detect_domain(text: str) -> str | None:
    """Detect legal domain from keywords in the query."""
    lower = text.lower()
    for keyword, domain in _DOMAIN_KEYWORDS.items():
        if keyword in lower:
            return domain
    return None


def infer_filters(analysis: QueryAnalysis) -> dict[str, Any]:
    """Infer metadata filters from query analysis.  Conservative: only set when confident."""
    filters: dict[str, Any] = {}
    if analysis.detected_document_type:
        filters["document_type"] = analysis.detected_document_type
    if analysis.detected_domain:
        filters["legal_domain"] = analysis.detected_domain
    return filters


def process_query(query: str) -> QueryAnalysis:
    """Full query processing pipeline."""
    normalized = normalize_whitespace(query)
    legal_refs = extract_legal_references(normalized)
    doc_type = detect_document_type(normalized)
    domain = detect_domain(normalized)

    analysis = QueryAnalysis(
        original_query=query,
        normalized_query=normalized,
        legal_references=legal_refs,
        detected_domain=domain,
        detected_document_type=doc_type,
    )
    analysis.filters = infer_filters(analysis)
    return analysis
