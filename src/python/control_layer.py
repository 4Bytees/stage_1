import sys
from pathlib import Path

# Definición unificada de la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR / "src" / "python") not in sys.path:
    sys.path.append(str(BASE_DIR / "src" / "python"))

CONTROL_DIR = BASE_DIR / "control"
DOWNLOADED_BOOKS_FILE = CONTROL_DIR / "downloaded_books.txt"
INDEXED_BOOKS_FILE = CONTROL_DIR / "indexed_books.txt"

CONTROL_DIR.mkdir(parents=True, exist_ok=True)

class ControlLayer:
    def __init__(self, crawler=None, metadata_service=None, indexer_service=None):
        self.crawler = crawler
        self.metadata_service = metadata_service
        self.indexer_service = indexer_service

    def get_processed_ids(self, file_path: Path) -> set:
        """Lee un archivo de control y devuelve el conjunto de IDs procesados."""
        if not file_path.exists():
            return set()
        with open(file_path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}

    def mark_as_processed(self, file_path: Path, book_id: str):
        """Añade de forma idempotente un ID al archivo de control correspondiente."""
        processed = self.get_processed_ids(file_path)
        if str(book_id) not in processed:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{book_id}\n")

    def run_pipeline(self, book_ids: list):
        """
        Ejecuta el pipeline real secuencialmente:
        Crawler -> Metadata Extraction -> Inverted Indexing
        """
        downloaded = self.get_processed_ids(DOWNLOADED_BOOKS_FILE)
        indexed = self.get_processed_ids(INDEXED_BOOKS_FILE)

        for book_id in book_ids:
            book_id_str = str(book_id)

            # Etapa 1: Descarga e Ingesta en Datalake
            if book_id_str not in downloaded:
                print(f"[CONTROL] Descargando libro ID: {book_id_str}...")
                if self.crawler:
                    success = self.crawler.download_and_store(book_id_str)
                    if success:
                        self.mark_as_processed(DOWNLOADED_BOOKS_FILE, book_id_str)
            else:
                print(f"[CONTROL] Libro ID: {book_id_str} ya existe en Datalake.")

            # Etapa 2: Extracción de Metadatos a SQLite
            if self.metadata_service:
                print(f"[CONTROL] Procesando metadatos para ID: {book_id_str}...")
                self.metadata_service.process_book(book_id_str)

            # Etapa 3: Indexación en Índice Invertido
            if book_id_str not in indexed:
                if self.indexer_service:
                    print(f"[CONTROL] Indexando cuerpo de libro ID: {book_id_str}...")
                    self.indexer_service.index_book(book_id_str)
                    self.mark_as_processed(INDEXED_BOOKS_FILE, book_id_str)
            else:
                print(f"[CONTROL] Libro ID: {book_id_str} ya está indexado. Omitiendo.")