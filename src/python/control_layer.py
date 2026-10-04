import os

<<<<<<< HEAD
class ControlLayer:
    def __init__(self, crawler, metadata_service, indexer_service, control_dir="control"):
        self.crawler = crawler
        self.metadata_service = metadata_service
        self.indexer_service = indexer_service
        self.control_dir = control_dir
=======
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTROL_DIR = BASE_DIR / "control"
DOWNLOADS_FILE = CONTROL_DIR / "downloaded_books.txt"
INDEXED_FILE = CONTROL_DIR / "indexed_books.txt"

PYTHON_SRC_DIR = Path(__file__).resolve().parent
if str(PYTHON_SRC_DIR) not in sys.path:
    sys.path.append(str(PYTHON_SRC_DIR))

from crawler_controller import CrawlerController
from metadata.metadata_parser import process_single_metadata
from indexer.indexer import process_single_indexing

RANGE_START = 1
RANGE_END = 15

def init_control_layer():
    CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    if not DOWNLOADS_FILE.exists():
        DOWNLOADS_FILE.touch()
    if not INDEXED_FILE.exists():
        INDEXED_FILE.touch()

def read_ids(file_path: Path) -> set[int]:
    if not file_path.exists():
        return set()
    with open(file_path, "r", encoding="utf-8") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}

def append_id(file_path: Path, book_id: int):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{book_id}\n")

def real_download_book(book_id: int) -> bool:
    datalake_path = BASE_DIR / "datalake" / "time"
    crawler = CrawlerController(
        datalake_path=datalake_path,
        logs_path=CONTROL_DIR,
        total_books=book_id,
        datalake_structure="date"
    )
    return crawler._fetch_and_save_book(book_id)

def run_pipeline_step(total_books_target: int = 15):
    init_control_layer()
    downloaded = read_ids(DOWNLOADS_FILE)
    indexed = read_ids(INDEXED_FILE)
    pending_to_index = downloaded - indexed

    if pending_to_index:
        book_id = sorted(list(pending_to_index))[0]
        print(f"[CONTROL] Procesando libro pendiente ID {book_id}...")
>>>>>>> feature/integracion-lucas
        
        self.downloaded_file = os.path.join(control_dir, "downloaded_books.txt")
        self.indexed_file = os.path.join(control_dir, "indexed_books.txt")
        
        os.makedirs(self.control_dir, exist_ok=True)
        self.downloaded_ids = self._load_ids(self.downloaded_file)
        self.indexed_ids = self._load_ids(self.indexed_file)

<<<<<<< HEAD
    def _load_ids(self, filepath):
        if not os.path.exists(filepath):
            return set()
        with open(filepath, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())

    def _mark_as_done(self, filepath, book_id, id_set):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{book_id}\n")
        id_set.add(str(book_id))

    def process_book(self, book_id):
        book_id_str = str(book_id)
        book_id_int = int(book_id)

        if book_id_str not in self.downloaded_ids:
            try:
                success = self.crawler.download(book_id_int)
            except Exception as e:
                if hasattr(self.crawler, "_crawl_book"):
                    success = self.crawler._crawl_book(book_id_int)
                elif hasattr(self.crawler, "download_and_store"):
                    success = self.crawler.download_and_store(book_id_int)
                else:
                    raise e

            if success or success is None:
                self._mark_as_done(self.downloaded_file, book_id_str, self.downloaded_ids)
=======
    for candidate_id in range(1, total_books_target + 1):
        if candidate_id not in downloaded:
            print(f"[CONTROL] Descargando nuevo candidato ID {candidate_id}...")
            if real_download_book(candidate_id):
                append_id(DOWNLOADS_FILE, candidate_id)
                print(f"[CONTROL] Libro ID {candidate_id} descargado y registrado.")
                return True
>>>>>>> feature/integracion-lucas
            else:
                print(f"[Error] The book could not be downloaded {book_id_str}")
                return

        if book_id_str not in self.indexed_ids:
            if hasattr(self.metadata_service, 'process_single_metadata'):
                self.metadata_service.process_single_metadata(book_id_str)
            elif hasattr(self.metadata_service, 'metadata_parser'):
                self.metadata_service.metadata_parser(book_id_str)

            if hasattr(self.indexer_service, 'process_single_indexing'):
                self.indexer_service.process_single_indexing(book_id_str)
            elif hasattr(self.indexer_service, 'index_book'):
                self.indexer_service.index_book(book_id_str)

            self._mark_as_done(self.indexed_file, book_id_str, self.indexed_ids)