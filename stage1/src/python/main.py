"""
Main entry point for the Stage-1 book-ingestion pipeline.

Usage
-----
    cd stage1/
    python src/python/main.py [--start START] [--end END]

Arguments
---------
--start INT  First book ID to process (default: 1)
--end   INT  Last book ID to process inclusive (default: 15)
"""

import sys
import os
import argparse
from pathlib import Path

# Make src/python importable regardless of invocation directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metadata.metadata_parser as metadata_module
import indexer.indexer as indexer_module
from crawler_controller import CrawlerController
from control_layer import ControlLayer


def _build_metadata_service():
    """Return an object/module that exposes process_single_metadata(book_id)."""
    # metadata_module is the metadata_parser module; it exposes the function
    # directly at module level – no class instantiation required.
    return metadata_module


def _build_indexer_service():
    """Return an object/module that exposes process_single_indexing(book_id) -> bool."""
    return indexer_module


def main(start: int = 1, end: int = 15) -> None:
    print("=== Starting Book Processing Pipeline ===")
    print(f"    Corpus range: IDs {start}–{end}  ({end - start + 1} books)")

    base_dir = Path(__file__).resolve().parent.parent.parent
    datalake_path = base_dir / "datalake" / "time"
    logs_path = base_dir / "control"

    datalake_path.mkdir(parents=True, exist_ok=True)
    logs_path.mkdir(parents=True, exist_ok=True)

    crawler = CrawlerController(
        datalake_path=datalake_path,
        logs_path=logs_path,
        total_books=end,
        datalake_structure="date"
    )

    metadata_service = _build_metadata_service()
    indexer_service = _build_indexer_service()

    control = ControlLayer(
        crawler=crawler,
        metadata_service=metadata_service,
        indexer_service=indexer_service,
        control_dir=logs_path,
    )

    for book_id in range(start, end + 1):
        print(f"\n--- Processing Book ID: {book_id} ---")
        control.process_book(book_id)

    print("\n=== Processing completed ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stage-1 book ingestion pipeline"
    )
    parser.add_argument("--start", type=int, default=1,
                        help="First book ID (inclusive, default 1)")
    parser.add_argument("--end", type=int, default=15,
                        help="Last book ID (inclusive, default 15)")
    args = parser.parse_args()
    main(start=args.start, end=args.end)