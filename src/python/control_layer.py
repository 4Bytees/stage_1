import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTROL_DIR = BASE_DIR / "control"
DOWNLOADS_FILE = CONTROL_DIR / "downloaded_books.txt"
INDEXED_FILE = CONTROL_DIR / "indexed_books.txt"

RANGE_START = 1001
RANGE_END = 1100

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

def mock_download_book(book_id: int) -> bool:
    print(f"[CONTROL] Simulación: Descargando libro ID {book_id}...")
    return True

def mock_index_book(book_id: int) -> bool:
    print(f"[CONTROL] Simulación: Indexando libro ID {book_id}...")
    return True

def run_pipeline_step():
    init_control_layer()
    
    downloaded = read_ids(DOWNLOADS_FILE)
    indexed = read_ids(INDEXED_FILE)
    
    pending_to_index = downloaded - indexed
    
    if pending_to_index:
        book_id = pending_to_index.pop()
        print(f"[CONTROL] Libro {book_id} preparado para indexar.")
        
        if mock_index_book(book_id):
            append_id(INDEXED_FILE, book_id)
            print(f"[CONTROL] Libro {book_id} registrado correctamente en indexed_books.txt.")
        return

    for candidate_id in range(RANGE_START, RANGE_END + 1):
        if candidate_id not in downloaded:
            print(f"[CONTROL] Candidato encontrado para descargar: {candidate_id}")
            
            if mock_download_book(candidate_id):
                append_id(DOWNLOADS_FILE, candidate_id)
                print(f"[CONTROL] Libro {candidate_id} registrado correctamente en downloaded_books.txt.")
            return

    print("[CONTROL] ¡Proceso finalizado! Todos los libros del rango han sido descargados e indexados.")

if __name__ == "__main__":
    print("--- Iniciando prueba de la Control Layer ---")
    for _ in range(3):
        run_pipeline_step()