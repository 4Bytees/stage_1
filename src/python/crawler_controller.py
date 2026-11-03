"""
CrawlerController: HTTP download engine for Project Gutenberg books.

The controller separates HTTP fetching (network I/O) from local disk I/O so
that each phase can be timed independently.  The public method ``download_book``
accepts a specific book ID and returns True/False – it is NOT a count-based API.
"""

from pathlib import Path
from storage.book_storage_date import BookStorageDate
from storage.book_storage_id import BookStorageId
from gutenberg_request import GutenbergRequest


class CrawlerController:
    """
    Parameters
    ----------
    datalake_path : str | Path
        Root directory for raw book storage.
    logs_path : str | Path
        Directory for control/audit files (downloaded_books.txt, etc.).
    total_books : int
        Upper bound of book IDs to consider when iterating.
    datalake_structure : {"date", "id"}
        Storage layout for newly downloaded books.
    """

    def __init__(self, datalake_path, logs_path,
                 total_books: int = 100, datalake_structure: str = "date"):
        self.requester = GutenbergRequest()
        self.storage = (
            BookStorageId(Path(datalake_path))
            if datalake_structure == "id"
            else BookStorageDate(Path(datalake_path))
        )
        self.datalake_structure = datalake_structure
        self.total_books = total_books
        self.logs_path = Path(logs_path)
        self.downloaded_path = self.logs_path / "downloaded_books.txt"
        self.failed_to_download_path = self.logs_path / "failed_to_download_books.txt"

        self.logs_path.mkdir(parents=True, exist_ok=True)
        if not self.downloaded_path.exists():
            self.downloaded_path.touch()
        if not self.failed_to_download_path.exists():
            self.failed_to_download_path.touch()

    # ------------------------------------------------------------------
    # State readers
    # ------------------------------------------------------------------

    def _downloaded(self) -> set[int]:
        content = self.downloaded_path.read_text(encoding="utf-8").splitlines()
        return {int(x) for x in content if x.strip().isdigit()}

    def _failed_to_download(self) -> set[int]:
        content = self.failed_to_download_path.read_text(encoding="utf-8").splitlines()
        return {int(x) for x in content if x.strip().isdigit()}

    # ------------------------------------------------------------------
    # Primary public interface (used by ControlLayer)
    # ------------------------------------------------------------------

    def download_book(self, book_id: int) -> bool:
        """
        Download a single book identified by *book_id* and persist it to the
        datalake.  Updates downloaded_books.txt or failed_to_download_books.txt
        accordingly.

        Returns
        -------
        bool
            True if the book was successfully fetched and saved; False otherwise.
        """
        if book_id in self._downloaded():
            print(f"[DOWNLOAD] Book {book_id} already downloaded. Skipping.")
            return True  # idempotent: already present

        if book_id in self._failed_to_download():
            print(f"[DOWNLOAD] Book {book_id} previously marked as failed. Skipping.")
            return False

        print(f"[DOWNLOAD] Fetching book ID {book_id} from Gutenberg...", flush=True)
        was_successful = self._fetch_and_save_book(book_id)

        if was_successful:
            with open(self.downloaded_path, "a", encoding="utf-8") as f:
                f.write(f"{book_id}\n")
            print(f"[DOWNLOAD] Book {book_id} saved successfully.")
        else:
            with open(self.failed_to_download_path, "a", encoding="utf-8") as f:
                f.write(f"{book_id}\n")
            print(f"[DOWNLOAD] Book {book_id} could not be saved.")

        return was_successful

    # ------------------------------------------------------------------
    # Batch convenience method (for standalone use only)
    # ------------------------------------------------------------------

    def download_batch(self, books_to_download: int = 1) -> None:
        """
        Download up to *books_to_download* books from the pending set
        ``range(1, total_books+1) - downloaded - failed``.
        Intended for standalone runs; not used by ControlLayer.
        """
        not_downloaded = (
            set(range(1, self.total_books + 1))
            - self._downloaded()
            - self._failed_to_download()
        )
        count = 0
        for candidate_id in sorted(not_downloaded):
            if count >= books_to_download:
                break
            if self.download_book(candidate_id):
                count += 1

        failed = self._failed_to_download()
        if failed:
            print(f"[DOWNLOAD] Books that could not be downloaded: {sorted(failed)}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_and_save_book(self, book_id: int) -> bool:
        """Fetch raw text from Gutenberg and persist both header and body files."""
        content = self.requester.fetch_book(book_id)
        if content:
            path = self.storage.save(book_id, content)
            if path:
                print(f"[DOWNLOAD] Book {book_id} stored at {path}")
                return True
            else:
                print(f"[DOWNLOAD] Book {book_id} discarded (no valid bookmarks)")
                return False
        else:
            print(f"[DOWNLOAD] Book {book_id} not found on Gutenberg")
            return False


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("--- Starting Crawler Controller Standalone Run ---")

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATALAKE_PATH = BASE_DIR / "datalake" / "time"
    LOGS_PATH = BASE_DIR / "control"

    crawler = CrawlerController(
        datalake_path=DATALAKE_PATH,
        logs_path=LOGS_PATH,
        total_books=10,
        datalake_structure="date"
    )

    crawler.download_batch(books_to_download=5)