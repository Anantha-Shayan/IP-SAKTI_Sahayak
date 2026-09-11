"""Conservative legal text cleaning."""

from __future__ import annotations

import re
from collections import Counter

PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s*)?\d+\s*$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def discover_repeated_marginal_lines(page_texts: list[str], max_lines: int = 3) -> set[str]:
    if len(page_texts) < 4:
        return set()
    candidates: list[str] = []
    for text in page_texts:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        candidates.extend(lines[:max_lines])
        candidates.extend(lines[-max_lines:])
    counts = Counter(candidates)
    threshold = max(3, int(len(page_texts) * 0.45))
    return {
        line
        for line, count in counts.items()
        if count >= threshold and len(line) <= 140 and not re.search(r"\b(section|article|rule|chapter)\b", line, re.I)
    }


def clean_page_text(text: str, repeated_lines: set[str] | None = None) -> str:
    text = normalize_text(text)
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if repeated_lines and stripped in repeated_lines:
            continue
        if PAGE_NUMBER_RE.match(stripped):
            continue
        lines.append(stripped)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(?<![.;:!?])\n(?!\n|[A-Z][A-Z\s]{3,}$|(?:CHAPTER|PART|SECTION|Article|Rule|Regulation)\b)", " ", cleaned)
    return normalize_text(cleaned)

