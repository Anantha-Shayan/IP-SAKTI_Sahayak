"""Deterministic document metadata inference from source evidence."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import CORPUS_ID, DATASET_DESCRIPTIONS, PROCESSOR_VERSION
from .hashing import sha256_text


def dataset_id_for(relative_path: str) -> str:
    return Path(relative_path).parts[0] if Path(relative_path).parts else "UNKNOWN"


def make_document_id(dataset_id: str, normalized_relative_path: str) -> str:
    return sha256_text(CORPUS_ID, dataset_id, normalized_relative_path)


def infer_title(filename: str, first_pages_text: str) -> str | None:
    lines = [ln.strip() for ln in first_pages_text.splitlines() if 8 <= len(ln.strip()) <= 180]
    for line in lines[:40]:
        if re.search(r"\b(Act|Rules|Regulations|Notification|Protocol|Treaty|Guidelines|Manual|Digest|Convention)\b", line, re.I):
            return re.sub(r"\s+", " ", line)
    stem = Path(filename).stem.replace("_", " ")
    return re.sub(r"\s+", " ", stem).strip() or None


def infer_document_type(filename: str, text: str, dataset_id: str) -> str:
    evidence = f"{filename}\n{text[:5000]}".lower()
    if "amendment act" in evidence:
        return "Amendment"
    if re.search(r"\bact,?\s+\d{4}\b", evidence) or "_act_" in evidence or evidence.endswith(" act"):
        return "Statute"
    if "case stud" in evidence or "digest" in evidence:
        return "Case_Study"
    if re.search(r"\b(judgment|judgement|court of|versus| v\. )\b", evidence):
        return "Case_Law"
    if "manual" in evidence or "practice and procedure" in evidence:
        return "Manual"
    if "guideline" in evidence:
        return "Guideline"
    if "protocol" in evidence:
        return "Protocol"
    if "treaty" in evidence or "convention" in evidence or "wipo gratk" in evidence:
        return "Treaty"
    if "notification" in evidence or "gazette" in evidence:
        return "Notification"
    if "regulation" in evidence:
        return "Regulation"
    if "rules" in evidence:
        return "Rule"
    if dataset_id == "Dataset_4_International":
        return "Treaty"
    return "Other"


def infer_jurisdiction(dataset_id: str, filename: str, text: str) -> str | None:
    evidence = f"{filename}\n{text[:5000]}".lower()
    if dataset_id == "Dataset_4_International":
        return "International"
    if "india" in evidence or "government of india" in evidence or dataset_id in {"Dataset_1", "Dataset_2", "Dataset_3_TK"}:
        return "India"
    return None


def infer_authority(jurisdiction: str | None, text: str) -> str | None:
    head = text[:5000].lower()
    if jurisdiction == "India" and ("government of india" in head or "ministry" in head or "gazette of india" in head or "the gazette of india" in head):
        return "Government of India"
    if "world intellectual property organization" in head or "wipo" in head:
        return "WIPO"
    if "convention on biological diversity" in head or "cbd" in head:
        return "Convention on Biological Diversity"
    return None


def infer_legal_domains(filename: str, text: str) -> list[str]:
    evidence = f"{filename}\n{text[:10000]}".lower()
    domains: list[str] = []
    checks = [
        ("patent law", ["patent"]),
        ("trademark law", ["trade mark", "trademark"]),
        ("biodiversity", ["biological diversity", "biodiversity", "biological resources"]),
        ("traditional knowledge", ["traditional knowledge", "tkdl", "indigenous", "gratk"]),
        ("drugs and cosmetics", ["drugs", "cosmetics"]),
        ("consumer protection", ["consumer protection", "ccpa"]),
        ("international law", ["treaty", "protocol", "convention", "wipo"]),
        ("intellectual property", ["intellectual property", "wipo", "patent", "trade mark", "trademark"]),
    ]
    for domain, needles in checks:
        if any(n in evidence for n in needles):
            domains.append(domain)
    return domains


def build_document_metadata(
    *,
    source_path: Path,
    raw_root: Path,
    source_sha256: str,
    page_count: int,
    first_pages_text: str,
) -> dict[str, Any]:
    relative_path = source_path.relative_to(raw_root).as_posix()
    dataset_id = dataset_id_for(relative_path)
    document_id = make_document_id(dataset_id, relative_path)
    jurisdiction = infer_jurisdiction(dataset_id, source_path.name, first_pages_text)
    metadata = {
        "processor_version": PROCESSOR_VERSION,
        "document_id": document_id,
        "corpus_id": CORPUS_ID,
        "dataset_id": dataset_id,
        "dataset_description": DATASET_DESCRIPTIONS.get(dataset_id),
        "filename": source_path.name,
        "relative_path": relative_path,
        "title": infer_title(source_path.name, first_pages_text),
        "document_type": infer_document_type(source_path.name, first_pages_text, dataset_id),
        "jurisdiction": jurisdiction,
        "authority": infer_authority(jurisdiction, first_pages_text),
        "language": "en" if re.search(r"[A-Za-z]{20,}", first_pages_text) else None,
        "legal_domains": infer_legal_domains(source_path.name, first_pages_text),
        "publication_date": None,
        "effective_date": None,
        "source_sha256": source_sha256,
        "page_count": page_count,
    }
    return metadata
