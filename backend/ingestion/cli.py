"""Command-line entrypoint for SIH26045 ingestion."""

from __future__ import annotations

import argparse
from pathlib import Path

from .logging_utils import configure_logging
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build embedding-ready SIH26045 chunks from raw PDFs.")
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/embedding_ready"))
    parser.add_argument("--ocr", action="store_true", help="Enable lazy OCR fallback for pages with inadequate text.")
    parser.add_argument("--workers", type=int, default=1, help="Reserved for future multiprocessing; currently processed serially.")
    parser.add_argument("--force", action="store_true", help="Force reprocessing even if previous outputs exist.")
    parser.add_argument("--validate-only", action="store_true", help="Extract and validate without writing chunks.jsonl.")
    parser.add_argument("--chunk-size", type=int, default=600)
    parser.add_argument("--chunk-overlap", type=int, default=80)
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_logging(args.verbose)
    run_pipeline(
        input_dir=args.input,
        output_dir=args.output,
        ocr=args.ocr,
        workers=args.workers,
        force=args.force,
        validate_only=args.validate_only,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )


if __name__ == "__main__":
    main()

