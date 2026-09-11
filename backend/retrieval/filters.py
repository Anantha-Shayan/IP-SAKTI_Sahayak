"""Optional metadata filters for retrieval.

Filters are always optional — never discard results solely because a weak
classifier guessed the wrong domain.
"""

from __future__ import annotations

from typing import Any

from .models import RetrievedChunk


def apply_metadata_filters(
    chunks: list[RetrievedChunk],
    filters: dict[str, Any],
) -> list[RetrievedChunk]:
    """Post-retrieval filtering on chunk metadata.  Returns only matching chunks."""
    if not filters:
        return chunks

    filtered: list[RetrievedChunk] = []
    for chunk in chunks:
        if _matches(chunk, filters):
            filtered.append(chunk)
    return filtered


def _matches(chunk: RetrievedChunk, filters: dict[str, Any]) -> bool:
    for key, value in filters.items():
        chunk_value = _get_field(chunk, key)
        if chunk_value is None:
            continue  # Don't exclude when metadata is missing
        if isinstance(value, list):
            if isinstance(chunk_value, list):
                if not set(value) & set(chunk_value):
                    return False
            elif chunk_value not in value:
                return False
        elif isinstance(chunk_value, list):
            if value not in chunk_value:
                return False
        elif chunk_value != value:
            return False
    return True


def _get_field(chunk: RetrievedChunk, key: str) -> Any:
    """Retrieve a field from the chunk by name."""
    return getattr(chunk, key, None)


# ---------------------------------------------------------------------------
# Exact Legal Reference Boosting (Step 2)
# ---------------------------------------------------------------------------

import re

# Recognize legal reference patterns
_BOOST_SECTION_RE = re.compile(r"\b(?:section|sec\.?)\s+(\d+[a-z]?(?:\(\w+\))*)", re.IGNORECASE)
_BOOST_ARTICLE_RE = re.compile(r"\b(?:article|art\.?)\s+(\d+[a-z]?(?:\(\w+\))*)", re.IGNORECASE)
_BOOST_RULE_RE = re.compile(r"\b(?:rule|regulation|reg\.?)\s+(\d+[a-z]?(?:\(\w+\))*)", re.IGNORECASE)

# Mapping from query act/law keywords to document filename tokens
_ACT_NAME_KEYWORDS: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"\bbiological\s+diversity\b|\bbiodiversity\b", re.I), ["biological_diversity", "biodiversity"]),
    (re.compile(r"\bpatents?\s+act\b", re.I), ["patents_act"]),
    (re.compile(r"\btrade\s*marks?\s+act\b", re.I), ["trade_marks", "trademark"]),
    (re.compile(r"\bdrugs?\s*(?:and|&)\s*cosmetics?\b", re.I), ["drugsandcosmetics", "drugs_and_cosmetics"]),
    (re.compile(r"\bmagic\s+remedies\b", re.I), ["magic_remedies"]),
    (re.compile(r"\bnagoya\s+protocol\b", re.I), ["nagoya_protocol", "nagoya"]),
    (re.compile(r"\bwipo\b", re.I), ["wipo"]),
    (re.compile(r"\btk\s+examination\s+guidelines\b|\bguidelines\s+for\s+examination\b", re.I), ["tk_examination_guidelines"]),
]


def apply_exact_reference_boost(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    legal_references: list[str] | None = None,
) -> list[RetrievedChunk]:
    """Boost chunks that match exact legal references and target documents mentioned in the query.

    Only activates when the query explicitly contains legal references (e.g. Section 3(1)(a), Article 5, Rule 12)
    or target act/treaty mentions.
    """
    if not chunks:
        return []

    # Check if query contains legal references
    found_refs: list[tuple[str, str, str]] = []  # (full_match, base_number, label)
    for pat, label in [(_BOOST_SECTION_RE, "section"), (_BOOST_ARTICLE_RE, "article"), (_BOOST_RULE_RE, "rule")]:
        for match in pat.finditer(query):
            full_ref = match.group(0).lower()
            num_part = match.group(1).lower()
            base_m = re.match(r"(\d+[a-z]?)", num_part)
            base_num = base_m.group(1) if base_m else num_part
            found_refs.append((full_ref, base_num, label))

    # Detect act/statute keywords in query
    matching_doc_tokens: list[str] = []
    for pat, tokens in _ACT_NAME_KEYWORDS:
        if pat.search(query):
            matching_doc_tokens.extend(tokens)

    # If neither legal references nor target act is in the query, return as-is
    if not found_refs and not matching_doc_tokens:
        return chunks

    boosted_chunks: list[RetrievedChunk] = []
    for chunk in chunks:
        boost = 0.0
        text_lower = chunk.text.lower()
        doc_lower = chunk.document_name.lower()
        chunk_sec = chunk.section.lower() if chunk.section else ""

        # Score legal reference matches
        for full_ref, base_num, label in found_refs:
            # Exact reference match in text (e.g. "section 3(1)(a)" or "section 3")
            if full_ref in text_lower:
                boost += 0.020
            # Base number match: "section 3"
            elif f"{label} {base_num}" in text_lower or f"{label}. {base_num}" in text_lower:
                boost += 0.012
            # Or chunk section metadata match:
            if chunk_sec and base_num in chunk_sec:
                boost += 0.010

        # Score document relevance
        if matching_doc_tokens:
            is_target_doc = any(tok in doc_lower for tok in matching_doc_tokens)
            if is_target_doc:
                boost += 0.015
            elif "guidelines" in doc_lower and not any("guidelines" in tok for tok in matching_doc_tokens):
                # When query explicitly targets an Act, secondary guidelines shouldn't outrank the primary Act
                boost -= 0.005

        if boost != 0.0:
            current_score = chunk.hybrid_score if chunk.hybrid_score is not None else chunk.score
            chunk.hybrid_score = current_score + boost
            chunk.score = chunk.hybrid_score

        boosted_chunks.append(chunk)

    # Re-sort by updated score
    boosted_chunks.sort(key=lambda c: c.hybrid_score if c.hybrid_score is not None else c.score, reverse=True)
    return boosted_chunks
