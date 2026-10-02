import os
import sys
from pathlib import Path

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

def run_pipeline_step():
    init_control_layer()
    downloaded = read_ids(DOWNLOADS_FILE)
    indexed = read_ids(INDEXED_FILE)

    pending_to_index = downloaded - indexed
    if pending_to_index:
        book_id = sorted(list(pending_to_index))[0]
        print(f"[CONTROL] Procesando libro pendiente ID {book_id}...")
        
        process_single_metadata(book_id)
        if process_single_indexing(book_id):
            append_id(INDEXED_FILE, book_id)
            print(f"[CONTROL] Libro ID {book_id} indexado y registrado exitosamente.")
        return True

    for candidate_id in range(RANGE_START, RANGE_END + 1):
        if candidate_id not in downloaded:
            print(f"[CONTROL] Descargando nuevo candidato ID {candidate_id}...")
            if real_download_book(candidate_id):
                append_id(DOWNLOADS_FILE, candidate_id)
                print(f"[CONTROL] Libro ID {candidate_id} descargado y registrado.")
                return True
            else:
                print(f"[CONTROL] Descarga fallida para libro ID {candidate_id}.")
                return False

    print("[CONTROL] Todos los libros objetivo han sido procesados.")
    return False

if __name__ == "__main__":
    print("--- Starting Connected Control Layer ---")
    run_pipeline_step()