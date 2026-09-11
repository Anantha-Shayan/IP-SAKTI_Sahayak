"""PDF discovery and extraction with lazy OCR fallback."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .config import CORPUS_ID, PROCESSOR_VERSION
from .hashing import sha256_text
from .models import PageRecord, ValidationMessage
from .text_cleaner import clean_page_text, discover_repeated_marginal_lines

LOG = logging.getLogger(__name__)


def discover_pdfs(raw_root: Path) -> list[Path]:
    return sorted(path for path in raw_root.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")


def printed_page_number(text: str) -> int | None:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[:5] + lines[-5:]:
        if re.fullmatch(r"(?:Page\s*)?(\d{1,4})", line, flags=re.I):
            return int(re.sub(r"\D", "", line))
    return None


def extract_pdf_pages(
    *,
    pdf_path: Path,
    document_id: str,
    dataset_id: str,
    ocr_enabled: bool = False,
) -> tuple[list[PageRecord], list[ValidationMessage], int]:
    try:
        import fitz  # type: ignore
    except ImportError:
        return _extract_with_poppler(pdf_path=pdf_path, document_id=document_id, dataset_id=dataset_id, ocr_enabled=ocr_enabled)

    messages: list[ValidationMessage] = []
    raw_texts: list[str] = []
    methods: list[str] = []
    failures: list[str | None] = []
    ocr_flags: list[bool] = []

    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    for idx in range(page_count):
        raw_text = ""
        method = "pymupdf_text"
        failure = None
        ocr_used = False
        try:
            page = doc.load_page(idx)
            raw_text = page.get_text("text", sort=True) or ""
            if _needs_ocr(raw_text) and ocr_enabled:
                ocr_text = _ocr_page(page)
                if ocr_text.strip():
                    raw_text = ocr_text
                    method = "ocr_tesseract"
                    ocr_used = True
                else:
                    failure = "OCR produced no usable text"
            elif _needs_ocr(raw_text):
                messages.append(
                    ValidationMessage(
                        "WARNING",
                        "OCR_NEEDED_BUT_DISABLED",
                        f"Page {idx + 1} has inadequate extracted text and OCR is disabled.",
                        document_id=document_id,
                        relative_path=pdf_path.name,
                        page_index=idx,
                    )
                )
        except Exception as exc:  # pragma: no cover - exercised by corrupt PDFs
            failure = str(exc)
            raw_text = ""
            messages.append(
                ValidationMessage(
                    "CRITICAL",
                    "PAGE_EXTRACTION_FAILED",
                    f"Failed to extract page {idx + 1}: {exc}",
                    document_id=document_id,
                    relative_path=pdf_path.name,
                    page_index=idx,
                )
            )
        raw_texts.append(raw_text)
        methods.append(method)
        failures.append(failure)
        ocr_flags.append(ocr_used)
    doc.close()

    repeated = discover_repeated_marginal_lines(raw_texts)
    pages: list[PageRecord] = []
    for idx, raw_text in enumerate(raw_texts):
        clean = clean_page_text(raw_text, repeated)
        page_id = sha256_text(document_id, idx)
        pages.append(
            PageRecord(
                processor_version=PROCESSOR_VERSION,
                corpus_id=CORPUS_ID,
                document_id=document_id,
                page_id=page_id,
                dataset_id=dataset_id,
                page_index=idx,
                pdf_page_number=idx + 1,
                printed_page_number=printed_page_number(raw_text),
                text=clean,
                raw_text=raw_text,
                character_count=len(clean),
                word_count=len(re.findall(r"\S+", clean)),
                ocr_used=ocr_flags[idx],
                extraction_method=methods[idx],
                extraction_failed=failures[idx] is not None,
                failure_reason=failures[idx],
                page_text_sha256=sha256_text(clean),
            )
        )
        if not clean.strip():
            messages.append(
                ValidationMessage(
                    "WARNING",
                    "EMPTY_PAGE_TEXT",
                    f"Page {idx + 1} has no extracted text.",
                    document_id=document_id,
                    relative_path=pdf_path.name,
                    page_index=idx,
                )
            )
    return pages, messages, page_count


def _extract_with_poppler(
    *,
    pdf_path: Path,
    document_id: str,
    dataset_id: str,
    ocr_enabled: bool,
) -> tuple[list[PageRecord], list[ValidationMessage], int]:
    if not shutil.which("pdftotext") or not shutil.which("pdfinfo"):
        raise RuntimeError("PDF extraction requires PyMuPDF, or Poppler tools pdfinfo and pdftotext on PATH.")
    messages: list[ValidationMessage] = [
        ValidationMessage(
            "WARNING",
            "PYMUPDF_UNAVAILABLE_POPPLER_FALLBACK",
            "PyMuPDF is unavailable; extracted text using Poppler pdftotext fallback.",
            document_id=document_id,
            relative_path=pdf_path.name,
        )
    ]
    info = subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True)
    match = re.search(r"^Pages:\s+(\d+)\s*$", info.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError("Unable to determine PDF page count with pdfinfo.")
    page_count = int(match.group(1))
    raw_texts: list[str] = []
    failures: list[str | None] = []
    for idx in range(page_count):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "page.txt"
                subprocess.run(
                    ["pdftotext", "-layout", "-enc", "UTF-8", "-f", str(idx + 1), "-l", str(idx + 1), str(pdf_path), str(out)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                raw_text = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
            failure = None
            if _needs_ocr(raw_text):
                code = "OCR_NEEDED_BUT_UNAVAILABLE" if ocr_enabled else "OCR_NEEDED_BUT_DISABLED"
                note = "OCR requested but Tesseract/PyMuPDF OCR path is unavailable." if ocr_enabled else "OCR is disabled."
                messages.append(
                    ValidationMessage(
                        "WARNING",
                        code,
                        f"Page {idx + 1} has inadequate extracted text. {note}",
                        document_id=document_id,
                        relative_path=pdf_path.name,
                        page_index=idx,
                    )
                )
        except Exception as exc:
            raw_text = ""
            failure = str(exc)
            messages.append(
                ValidationMessage(
                    "CRITICAL",
                    "PAGE_EXTRACTION_FAILED",
                    f"Failed to extract page {idx + 1}: {exc}",
                    document_id=document_id,
                    relative_path=pdf_path.name,
                    page_index=idx,
                )
            )
        raw_texts.append(raw_text)
        failures.append(failure)

    repeated = discover_repeated_marginal_lines(raw_texts)
    pages: list[PageRecord] = []
    for idx, raw_text in enumerate(raw_texts):
        clean = clean_page_text(raw_text, repeated)
        page_id = sha256_text(document_id, idx)
        pages.append(
            PageRecord(
                processor_version=PROCESSOR_VERSION,
                corpus_id=CORPUS_ID,
                document_id=document_id,
                page_id=page_id,
                dataset_id=dataset_id,
                page_index=idx,
                pdf_page_number=idx + 1,
                printed_page_number=printed_page_number(raw_text),
                text=clean,
                raw_text=raw_text,
                character_count=len(clean),
                word_count=len(re.findall(r"\S+", clean)),
                ocr_used=False,
                extraction_method="poppler_pdftotext",
                extraction_failed=failures[idx] is not None,
                failure_reason=failures[idx],
                page_text_sha256=sha256_text(clean),
            )
        )
        if not clean.strip():
            messages.append(
                ValidationMessage(
                    "WARNING",
                    "EMPTY_PAGE_TEXT",
                    f"Page {idx + 1} has no extracted text.",
                    document_id=document_id,
                    relative_path=pdf_path.name,
                    page_index=idx,
                )
            )
    return pages, messages, page_count


def _needs_ocr(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 40:
        return True
    words = re.findall(r"[A-Za-z]{2,}", stripped)
    return len(words) < 8


def _ocr_page(page: Any) -> str:
    try:
        import pytesseract  # type: ignore
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR requested but pytesseract/Pillow is unavailable") from exc
    pix = page.get_pixmap(matrix=None, dpi=250, alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(image, lang="eng")
