import os
import sys
from pathlib import Path

# Configuración de rutas principales
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTROL_DIR = BASE_DIR / "control"
DOWNLOADS_FILE = CONTROL_DIR / "downloaded_books.txt"
INDEXED_FILE = CONTROL_DIR / "indexed_books.txt"

# Añadir la carpeta src/python al PATH para importar los módulos correctamente
PYTHON_SRC_DIR = Path(__file__).resolve().parent
if str(PYTHON_SRC_DIR) not in sys.path:
    sys.path.append(str(PYTHON_SRC_DIR))

# Importación de la función individual del módulo de Metadatos
try:
    from metadata.metadata_parser import process_single_metadata
except ImportError:
    process_single_metadata = None

# Configuración de rangos para pruebas iterativas (Benchmarking)
RANGE_START = 1001
RANGE_END = 1100

def init_control_layer():
    """Garantiza la existencia de la carpeta de control y sus archivos."""
    CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    if not DOWNLOADS_FILE.exists():
        DOWNLOADS_FILE.touch()
    if not INDEXED_FILE.exists():
        INDEXED_FILE.touch()

def read_ids(file_path: Path) -> set[int]:
    """Lee un archivo de registro de la capa de control y devuelve los IDs numéricos."""
    if not file_path.exists():
        return set()
    with open(file_path, "r", encoding="utf-8") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}

def append_id(file_path: Path, book_id: int):
    """Escribe un ID procesado en el archivo de control correspondiente."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{book_id}\n")

# --- MOCK FUNCTIONS (Sustituibles por integraciones reales) ---
def mock_download_book(book_id: int) -> bool:
    """Simulación de descarga para pruebas aisladas."""
    print(f"[CONTROL] Mocking download for book ID {book_id}...")
    return True

def mock_index_book(book_id: int) -> bool:
    """Simulación de indexación para pruebas aisladas."""
    print(f"[CONTROL] Mocking indexing for book ID {book_id}...")
    return True

# --- PIPELINE DE ORQUESTACIÓN ---
def run_pipeline_step():
    """Ejecuta un ciclo de decisión del orquestador."""
    init_control_layer()
    
    downloaded = read_ids(DOWNLOADS_FILE)
    indexed = read_ids(INDEXED_FILE)
    
    # 1. Comprobar si hay libros descargados pendientes de indexar/procesar
    pending_to_index = downloaded - indexed
    
    if pending_to_index:
        book_id = pending_to_index.pop()
        print(f"[CONTROL] Book ID {book_id} ready for processing.")
        
        # Procesar únicamente los metadatos del libro actual
        if process_single_metadata:
            process_single_metadata(book_id)
            
        # Llamada al proceso de Indexación (Inverted Index)
        if mock_index_book(book_id):
            append_id(INDEXED_FILE, book_id)
            print(f"[CONTROL] Book ID {book_id} successfully recorded in indexed_books.txt.")
        return

    # 2. Si no hay pendientes de indexar, buscar el siguiente libro para descargar
    for candidate_id in range(RANGE_START, RANGE_END + 1):
        if candidate_id not in downloaded:
            print(f"[CONTROL] Candidate found for download: ID {candidate_id}")
            
            if mock_download_book(candidate_id):
                append_id(DOWNLOADS_FILE, candidate_id)
                print(f"[CONTROL] Book ID {candidate_id} successfully recorded in downloaded_books.txt.")
            return

    print("[CONTROL] Pipeline execution completed! All target books have been processed.")

if __name__ == "__main__":
    print("--- Starting Control Layer Orchestration ---")
    # Ejecuta 3 ciclos de orquestación a modo de prueba
    for _ in range(3):
        run_pipeline_step()