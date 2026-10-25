"""
ControlLayer: Idempotent supervisor for the book ingestion and indexing pipeline.

Tracks downloaded and indexed book IDs via plain-text state files in the
control/ directory.  A book is only recorded as indexed if the full metadata-
extraction + inverted-index pipeline completes without raising an exception.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve project root regardless of the working directory at invocation time
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTROL_DIR = BASE_DIR / "control"
DOWNLOADS_FILE = CONTROL_DIR / "downloaded_books.txt"
INDEXED_FILE = CONTROL_DIR / "indexed_books.txt"
FAILED_FILE = CONTROL_DIR / "failed_to_download_books.txt"

PYTHON_SRC_DIR = Path(__file__).resolve().parent
if str(PYTHON_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC_DIR))


class ControlLayer:

    def __init__(self, crawler, metadata_service, indexer_service,
                 control_dir: str | Path = CONTROL_DIR):
        self.crawler = crawler
        self.metadata_service = metadata_service
        self.indexer_service = indexer_service
        self.control_dir = Path(control_dir)

        self.downloaded_file = self.control_dir / "downloaded_books.txt"
        self.indexed_file = self.control_dir / "indexed_books.txt"
        self.failed_file = self.control_dir / "failed_to_download_books.txt"

        self.control_dir.mkdir(parents=True, exist_ok=True)
        for f in (self.downloaded_file, self.indexed_file, self.failed_file):
            if not f.exists():
                f.touch()

        self.downloaded_ids: set[str] = self._load_ids(self.downloaded_file)
        self.indexed_ids: set[str] = self._load_ids(self.indexed_file)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_ids(filepath: Path) -> set[str]:
        """Return the set of book-ID strings recorded in *filepath*."""
        if not filepath.exists():
            return set()
        with open(filepath, "r", encoding="utf-8") as fh:
            return {line.strip() for line in fh if line.strip().isdigit()}

    def _mark_as_done(self, filepath: Path, book_id: str, id_set: set[str]):
        """Append *book_id* to *filepath* and update the in-memory *id_set*."""
        with open(filepath, "a", encoding="utf-8") as fh:
            fh.write(f"{book_id}\n")
        id_set.add(book_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_book(self, book_id: int) -> None:
        book_id_str = str(book_id)

        # ---- 1. Download phase ----
        if book_id_str not in self.downloaded_ids:
            print(f"[CONTROL] Downloading book ID {book_id}...")
            try:
                success = self.crawler.download_book(book_id)
            except Exception as exc:
                print(f"[CONTROL ERROR] Download failed for book {book_id}: {exc}")
                return

            if success:
                self._mark_as_done(self.downloaded_file, book_id_str,
                                   self.downloaded_ids)
                print(f"[CONTROL] Book ID {book_id} recorded as downloaded.")
            else:
                print(f"[CONTROL] Book ID {book_id} could not be downloaded.")
                return

        # ---- 2. Indexing phase ----
        if book_id_str not in self.indexed_ids:
            print(f"[CONTROL] Indexing book ID {book_id}...")
            try:
                self.metadata_service.process_single_metadata(book_id)
                indexed_ok = self.indexer_service.process_single_indexing(book_id)
                if not indexed_ok:
                    print(f"[CONTROL] Indexer returned False for book {book_id}; "
                          "not marking as indexed.")
                    return
            except Exception as exc:
                print(f"[CONTROL ERROR] Indexing failed for book {book_id}: {exc}")
                return  # Do NOT mark as indexed on failure

            self._mark_as_done(self.indexed_file, book_id_str, self.indexed_ids)
            print(f"[CONTROL] Book ID {book_id} fully indexed and recorded.")
        else:
            print(f"[CONTROL] Book ID {book_id} already indexed. Skipping.")

    # ------------------------------------------------------------------
    # Discovery helper
    # ------------------------------------------------------------------

    def discover_pending_indexing(self) -> list[int]:
        downloaded = self._load_ids(self.downloaded_file)
        indexed = self._load_ids(self.indexed_file)
        pending = sorted(int(b) for b in (downloaded - indexed))
        return pending