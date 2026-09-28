from pathlib import Path
from storage.book_storage_date import BookStorageDate
from storage.book_storage_id import BookStorageId
from gutenberg_request import GutenbergRequest

class CrawlerController:
    def __init__(self, datalake_path, logs_path, total_books=100, datalake_structure="date"):
        self.requester = GutenbergRequest()
        self.storage = BookStorageId(Path(datalake_path)) if datalake_structure == "id" else BookStorageDate(Path(datalake_path))
        self.datalake = datalake_structure
        self.total_books = total_books
        self.logs_path = Path(logs_path)
        self.control_path = self.logs_path
        self.downloaded_path = self.logs_path / "downloaded_books.txt"
        self.failed_to_download_path = self.logs_path / "failed_to_download_books.txt"
        
        # Nos aseguramos de que existan los archivos de la Capa de Control
        self.logs_path.mkdir(parents=True, exist_ok=True)
        if not self.downloaded_path.exists():
            self.downloaded_path.touch()
        if not self.failed_to_download_path.exists():
            self.failed_to_download_path.touch()

        self.not_downloaded = set(range(1, self.total_books + 1)) - self._downloaded()

    def _downloaded(self):
        if self.downloaded_path.exists():
            content = self.downloaded_path.read_text().splitlines()
            return set(int(x) for x in content if x.strip().isdigit())
        return set()

    def _failed_to_download(self):
        if self.failed_to_download_path.exists():
            content = self.failed_to_download_path.read_text().splitlines()
            return set(int(x) for x in content if x.strip().isdigit())
        return set()

    def download(self, books_to_download=1):
        for _ in range(books_to_download):
            if not self._crawl_book():
                break

        self.not_downloaded = set(range(1, self.total_books + 1)) - self._downloaded()

        if self._failed_to_download():
            print("[DOWNLOAD] Los siguientes libros no se pudieron descargar:", sorted(list(self._failed_to_download())))

    def _crawl_book(self):
        if self.not_downloaded:
            candidate_id = self.not_downloaded.pop()
            while candidate_id in self._failed_to_download():
                if self.not_downloaded:
                    candidate_id = self.not_downloaded.pop()
                else:
                    return False
        else:
            print("[DOWNLOAD] No hay más libros pendientes de descarga.")
            return False

        print(f"[DOWNLOAD] Descargando nuevo libro con ID {candidate_id}...")
        was_successful = self._fetch_and_save_book(candidate_id)
        
        if was_successful:
            with open(self.downloaded_path, "a", encoding="utf-8") as f:
                f.write(f"{candidate_id}\n")
        else:
            with open(self.failed_to_download_path, "a", encoding="utf-8") as f:
                f.write(f"{candidate_id}\n")
        return True

    def _fetch_and_save_book(self, book_id):
        content = self.requester.fetch_book(book_id)

        if content:
            path = self.storage.save(book_id, content)
            if path:
                print(f"[DOWNLOAD] Libro {book_id} successfully found and saved at {path}", "\n")
                return True
            else:
                print(f"[DOWNLOAD] Libro {book_id} descarted (No valid bookmarks)\n")
                return False
        else:
            print(f"[DOWNLOAD] Libro {book_id} dont find in Gutenberg\n")
            return False