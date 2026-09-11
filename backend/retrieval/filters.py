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
