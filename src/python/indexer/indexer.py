from pathlib import Path
import sys


PYTHON_ROOT = Path(__file__).resolve().parent.parent

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


from tokenizer import tokenize
from indexer.base_container import (
    BASE_DIR,
    DATALAKE_DIR,
    DATAMARTS_DIR,
)
from indexer.containers.hierarchical_indexer import (
    HierarchicalFolderStructure,
)
from indexer.containers.monolithic_indexer import MonolithicIndexer
from indexer.containers.sqlite_indexer import SqliteIndexer


def find_body_file(
    book_id: int,
    corpus_dir: Path | str | None = None,
) -> Path | None:
    filenames = {
        f"{book_id}_body.txt",
        f"{book_id}.body.txt",
    }

    roots = (
        [Path(corpus_dir)]
        if corpus_dir is not None
        else [DATALAKE_DIR, BASE_DIR / "sample_data"]
    )

    for root in roots:
        if not root.exists():
            continue

        matches = sorted({
            path.resolve()
            for path in root.rglob("*")
            if path.is_file() and path.name in filenames
        })

        if len(matches) > 1:
            details = "\n".join(str(path) for path in matches)
            raise ValueError(
                f"Hay varias copias del libro {book_id} en {root}:\n"
                f"{details}\n"
                "Indica body_path o un corpus_dir mas concreto."
            )

        if matches:
            return matches[0]

    return None


def process_single_indexing(
    book_id: int,
    *,
    body_path: Path | str | None = None,
    corpus_dir: Path | str | None = None,
    output_dir: Path | str = DATAMARTS_DIR,
) -> bool:
    current_stage = "localizacion del texto"

    try:
        if body_path is not None and corpus_dir is not None:
            raise ValueError(
                "Indica body_path o corpus_dir, pero no ambos."
            )

        source = (
            Path(body_path)
            if body_path is not None
            else find_body_file(book_id, corpus_dir)
        )

        if source is None or not source.is_file():
            print(f"[INDEXER] No se encuentra el texto del libro {book_id}.")
            return False

        current_stage = "lectura UTF-8"
        text = source.read_text(encoding="utf-8")

        current_stage = "tokenizacion"
        position_dict = tokenize(text)

        destination = Path(output_dir)

        # Crear y guardar cada contenedor dentro del bloque de errores.
        current_stage = "indice monolitico"
        MonolithicIndexer(
            output_path=destination / "inverted_index.json",
        ).save_index_for_book(book_id, position_dict)

        current_stage = "indice jerarquico"
        HierarchicalFolderStructure(
            output_folder=destination / "inverted_index_folders",
        ).save_index_for_book(book_id, position_dict)

        current_stage = "indice SQLite"
        SqliteIndexer(
            db_path=destination / "inverted_index.db",
        ).save_index_for_book(book_id, position_dict)

        print(
            f"[INDEXER] Libro {book_id} indexado "
            "en los tres datamarts."
        )
        return True

    except Exception as error:
        print(
            f"[INDEXER ERROR] Libro {book_id}; "
            f"fase: {current_stage}; error: {error}"
        )
        print(
            "[INDEXER] Puede haber escrituras parciales. "
            "Corrige el error y repite la indexacion del libro."
        )
        return False


def discover_book_ids(corpus_dir: Path | str) -> list[int]:
    root = Path(corpus_dir)
    book_ids = set()

    if not root.exists():
        return []

    for path in root.rglob("*.txt"):
        if not path.is_file():
            continue

        for suffix in ("_body.txt", ".body.txt"):
            if path.name.endswith(suffix):
                identifier = path.name[:-len(suffix)]

                if identifier.isdigit():
                    book_ids.add(int(identifier))

                break

    return sorted(book_ids)


if __name__ == "__main__":
    corpus = BASE_DIR / "sample_data"
    target_ids = discover_book_ids(corpus)

    if not target_ids:
        print(f"[INDEXER] No hay textos de libros en {corpus}.")
        sys.exit(1)

    success = True

    for book_id in target_ids:
        result = process_single_indexing(
            book_id,
            corpus_dir=corpus,
        )
        success = result and success

    sys.exit(0 if success else 1)