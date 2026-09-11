"""CLI for offline dense/BM25/Qdrant indexing."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from backend.ingestion.logging_utils import configure_logging

from .config import IndexingConfig
from .pipeline import build_indexes, config_with_overrides, validate_existing
from .validation import validation_status


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build offline SIH26045 indexes from embedding-ready chunks.")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ["build", "validate"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--chunks", type=Path)
        cmd.add_argument("--output", type=Path)
        cmd.add_argument("--embedding-provider")
        cmd.add_argument("--embedding-model")
        cmd.add_argument("--device")
        cmd.add_argument("--batch-size", type=int)
        cmd.add_argument("--qdrant-mode")
        cmd.add_argument("--qdrant-url")
        cmd.add_argument("--qdrant-collection")
        cmd.add_argument("--qdrant-distance")
        cmd.add_argument("--qdrant-upsert-batch-size", type=int)
        cmd.add_argument("--index-collision-documents", choices=["true", "false"])
        cmd.add_argument("--verbose", action="store_true")
    build = sub.choices["build"]
    build.add_argument("--rebuild", action="store_true")
    build.add_argument("--skip-embeddings", action="store_true")
    build.add_argument("--skip-bm25", action="store_true")
    build.add_argument("--skip-qdrant", action="store_true")
    return p


def main() -> None:
    args = parser().parse_args()
    configure_logging(args.verbose)
    config = config_with_overrides(
        IndexingConfig(),
        chunks=args.chunks,
        output=args.output,
        embedding_provider=args.embedding_provider,
        embedding_model=args.embedding_model,
        device=args.device,
        batch_size=args.batch_size,
        qdrant_mode=args.qdrant_mode,
        qdrant_url=args.qdrant_url,
        qdrant_collection=args.qdrant_collection,
        qdrant_distance=args.qdrant_distance,
        qdrant_upsert_batch_size=args.qdrant_upsert_batch_size,
        index_collision_documents=None if args.index_collision_documents is None else args.index_collision_documents == "true",
    )
    if args.command == "build":
        result = build_indexes(
            config=config,
            rebuild=args.rebuild,
            skip_embeddings=args.skip_embeddings,
            skip_bm25=args.skip_bm25,
            skip_qdrant=args.skip_qdrant,
        )
    else:
        result = validate_existing(config)
    status = validation_status(result["validation_messages"])
    logging.info("Index validation result: %s", status)
    if status == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

