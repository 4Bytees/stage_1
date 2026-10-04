import os
from pathlib import Path
import sys

PYTHON_ROOT = Path(__file__).resolve().parent.parent
if str(PYTHON_ROOT) not in sys.path:
  sys.path.insert(0, str(PYTHON_ROOT))

from indexer.base_container import DATALAKE_DIR, BASE_DIR
from indexer.containers.hierarchical_indexer import HierarchicalFolderStructure
from indexer.containers.monolitic_indexer import MonoliticIndexer
from indexer.containers.sqlite_indexer import SqliteIndexer


def find_body_file(book_id: int) -> Path | None:
    target_files = [f"{book_id}_body.txt", f"{book_id}.body.txt"]
    if DATALAKE_DIR.exists():
        for root, _, files in os.walk(DATALAKE_DIR):
            for file in files:
                if file in target_files:
                    return Path(root) / file
    sample_dir = BASE_DIR / "sample_data"
    if sample_dir.exists():
        for root, _, files in os.walk(sample_dir):
            for file in files:
                if file in target_files:
                    return Path(root) / file
    return None


def process_single_indexing(book_id: int) -> bool:
  body_path = find_body_file(book_id)
  if not body_path or not body_path.exists():
    print(f"[INDEXER] Archivo _body.txt para libro {book_id} no encontrado.")
    return False

  try:
    text = body_path.read_text(encoding="utf-8", errors="ignore")

    monolithic = MonoliticIndexer()
    hierarchical = HierarchicalFolderStructure()
    sqlite_idx = SqliteIndexer()

    position_dict = monolithic.tokenize(text)

    monolithic.save_index_for_book(book_id, position_dict)
    hierarchical.save_index_for_book(book_id, position_dict)
    sqlite_idx.save_index_for_book(book_id, position_dict)

    print(f"[INDEXER] Libro ID {book_id} indexado con éxito en los 3 datamarts.")
    return True
  except Exception as e:
    print(f"[INDEXER ERROR] Fallo al indexar libro {book_id}: {e}")
    return False


if __name__ == "__main__":
    print("--- Running Inverted Indexer Standalone Test ---")
    target_ids = []
    sample_dir = BASE_DIR / "sample_data"
    if sample_dir.exists():
        for f in sample_dir.glob("*_body.txt"):
            b_id = f.stem.split("_")[0]
            if b_id.isdigit():
                target_ids.append(int(b_id))
    
    for b_id in sorted(set(target_ids)):
        process_single_indexing(b_id)