"""Legal/traditional-knowledge structure detection."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

STRUCTURE_KEYS = [
    "part",
    "chapter",
    "sub_chapter",
    "section",
    "subsection",
    "clause",
    "sub_clause",
    "proviso",
    "explanation",
    "schedule",
    "article",
    "rule",
    "regulation",
    "case_name",
    "court",
    "case_number",
    "judgment",
    "order",
]

PATTERNS = [
    ("part", re.compile(r"^\s*(PART\s+[IVXLCDM0-9A-Z]+)\b", re.I)),
    ("chapter", re.compile(r"^\s*(CHAPTER\s+[IVXLCDM0-9A-Z]+)\b", re.I)),
    ("sub_chapter", re.compile(r"^\s*(SUB-?CHAPTER\s+[IVXLCDM0-9A-Z]+)\b", re.I)),
    ("schedule", re.compile(r"^\s*(THE\s+)?((?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|\d+)(?:\s+SCHEDULE)|SCHEDULE\s+[IVXLCDM0-9A-Z]*)\b", re.I)),
    ("section", re.compile(r"^\s*(?:Section\s+)?(\d+[A-Z]?)\.\s+|^\s*Section\s+(\d+[A-Z]?)\b", re.I)),
    ("article", re.compile(r"^\s*(Article\s+\d+[A-Z]?)\b", re.I)),
    ("rule", re.compile(r"^\s*(Rule\s+\d+[A-Z]?|\d+[A-Z]?\.\s+)", re.I)),
    ("regulation", re.compile(r"^\s*(Regulation\s+\d+[A-Z]?)\b", re.I)),
    ("subsection", re.compile(r"^\s*(\(\d+[A-Z]?\))\s+")),
    ("clause", re.compile(r"^\s*(\([a-z]{1,3}\))\s+")),
    ("sub_clause", re.compile(r"^\s*(\([ivxlcdm]+\))\s+", re.I)),
    ("proviso", re.compile(r"^\s*(Provided\s+that|PROVIDED\s+that)\b")),
    ("explanation", re.compile(r"^\s*(Explanation(?:\s+\d+)?)\b", re.I)),
    ("judgment", re.compile(r"^\s*(JUDGMENT|JUDGEMENT)\b", re.I)),
    ("order", re.compile(r"^\s*(ORDER)\b", re.I)),
]

CASE_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9 .,&'()/-]+\s+(?:v\.|vs\.|versus)\s+[A-Z][A-Za-z0-9 .,&'()/-]+)\s*$", re.I)
CASE_NO_RE = re.compile(r"\b((?:Civil|Criminal|Writ|Appeal|Petition|Suit|Application)[A-Za-z .]*No\.?\s*[\w./ -]+)", re.I)
COURT_RE = re.compile(r"\b(Supreme Court of India|High Court of [A-Za-z ]+|Court of [A-Za-z ]+)\b", re.I)


def empty_structure() -> dict[str, Any]:
    return {key: None for key in STRUCTURE_KEYS}


def update_structure_from_line(context: dict[str, Any], line: str) -> dict[str, Any]:
    current = deepcopy(context)
    case_match = CASE_RE.match(line)
    if case_match and not current.get("case_name"):
        current["case_name"] = re.sub(r"\s+", " ", case_match.group(1)).strip()
    case_no = CASE_NO_RE.search(line)
    if case_no and not current.get("case_number"):
        current["case_number"] = re.sub(r"\s+", " ", case_no.group(1)).strip()
    court = COURT_RE.search(line)
    if court and not current.get("court"):
        current["court"] = re.sub(r"\s+", " ", court.group(1)).strip()

    for key, pattern in PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        value = next((g for g in match.groups() if g), match.group(0))
        value = re.sub(r"\s+", " ", value).strip()
        if key == "section" and not value.lower().startswith("section"):
            value = f"Section {value.rstrip('.')}"
        if key == "rule" and value.endswith("."):
            value = f"Rule {value.rstrip('.')}"
        current[key] = value
        if key in {"part", "chapter", "article", "section", "rule", "regulation", "schedule"}:
            for lower in ["subsection", "clause", "sub_clause", "proviso", "explanation"]:
                current[lower] = None
        if key == "subsection":
            for lower in ["clause", "sub_clause", "proviso", "explanation"]:
                current[lower] = None
        if key == "clause":
            for lower in ["sub_clause", "proviso", "explanation"]:
                current[lower] = None
        break
    return current


def annotate_page_structure(text: str, inherited: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    context = deepcopy(inherited) if inherited else empty_structure()
    first_context = deepcopy(context)
    for line in text.splitlines():
        before = deepcopy(context)
        context = update_structure_from_line(context, line)
        if first_context == before and context != before:
            first_context = deepcopy(context)
    return first_context, context


def split_structural_blocks(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    context = empty_structure()
    boundary_keys = {"part", "chapter", "schedule", "section", "article", "rule", "regulation", "judgment", "order"}

    for page in pages:
        page_no = page["pdf_page_number"]
        for para in _paragraphs(page["text"]):
            new_context = deepcopy(context)
            for line in para.splitlines():
                new_context = update_structure_from_line(new_context, line)
            boundary = current is None or any(new_context.get(k) != context.get(k) and new_context.get(k) for k in boundary_keys)
            if boundary:
                if current:
                    blocks.append(current)
                current = {
                    "text": para,
                    "page_start": page_no,
                    "page_end": page_no,
                    "printed_page_start": page.get("printed_page_number"),
                    "printed_page_end": page.get("printed_page_number"),
                    "structure": deepcopy(new_context),
                }
            else:
                current["text"] += "\n\n" + para
                current["page_end"] = page_no
                current["printed_page_end"] = page.get("printed_page_number")
                current["structure"] = deepcopy(new_context)
            context = new_context
    if current:
        blocks.append(current)
    return blocks


def _paragraphs(text: str) -> list[str]:
    raw = re.split(r"\n\s*\n", text.strip())
    paras = [p.strip() for p in raw if p.strip()]
    if len(paras) <= 1:
        paras = [p.strip() for p in text.splitlines() if p.strip()]
    return paras
