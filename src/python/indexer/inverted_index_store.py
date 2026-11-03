from abc import ABC, abstractmethod
import json
from pathlib import Path
import re
import sqlite3


def normalize_term(term: str) -> str:
    term = term.lower()

    if re.fullmatch(r"[a-z]{3,}", term) is None:
        raise ValueError(
            "La consulta debe ser un termino ASCII de al menos tres letras."
        )

    return term


def validate_posting(book_id, frequency, positions) -> dict:
    if type(book_id) is not int or book_id < 0:
        raise ValueError("ID de libro invalido.")

    if type(frequency) is not int or frequency < 0:
        raise ValueError("Frecuencia invalida.")

    if not isinstance(positions, list):
        raise ValueError("Las posiciones deben ser una lista.")

    if any(type(position) is not int or position < 0 for position in positions):
        raise ValueError("Las posiciones deben ser enteros no negativos.")

    if frequency != len(positions):
        raise ValueError("La frecuencia no coincide con las posiciones.")

    if any(a >= b for a, b in zip(positions, positions[1:])):
        raise ValueError("Las posiciones deben ser estrictamente crecientes.")

    return {
        "book_id": book_id,
        "frequency": frequency,
        "positions": positions,
    }


def sorted_postings(postings: list[dict]) -> list[dict]:
    book_ids = [posting["book_id"] for posting in postings]

    if len(book_ids) != len(set(book_ids)):
        raise ValueError("Hay entradas duplicadas para un mismo libro.")

    return sorted(postings, key=lambda posting: posting["book_id"])


class InvertedIndexStore(ABC):
    @abstractmethod
    def query(self, term: str) -> list[dict]:
        pass


class MonolithicIndexStore(InvertedIndexStore):
    """
    Carga el JSON una vez al construir el lector.

    Si el indice cambia, crea una instancia nueva.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)

        with self.path.open("r", encoding="utf-8") as file:
            self.index = json.load(file)

        if not isinstance(self.index, dict):
            raise ValueError("El indice JSON debe contener un objeto.")

    def query(self, term: str) -> list[dict]:
        term = normalize_term(term)
        raw = self.index.get(term, {})

        if not isinstance(raw, dict):
            raise ValueError(f"Entradas invalidas para {term!r}.")

        postings = []

        for book_id, data in raw.items():
            if not isinstance(data, dict):
                raise ValueError(f"Entrada invalida para el libro {book_id}.")

            postings.append(
                validate_posting(
                    int(book_id),
                    data["frequency"],
                    data["positions"],
                )
            )

        return sorted_postings(postings)


class HierarchicalIndexStore(InvertedIndexStore):
    RESERVED_NAMES = frozenset(
        {"CON", "PRN", "AUX", "NUL"}
        | {f"COM{i}" for i in range(1, 10)}
        | {f"LPT{i}" for i in range(1, 10)}
    )

    def __init__(self, folder: Path | str):
        self.folder = Path(folder)

        if not self.folder.is_dir():
            raise FileNotFoundError(
                f"No existe el indice jerarquico: {self.folder}"
            )

    def term_path(self, term: str) -> Path:
        term = normalize_term(term)

        filename = (
            f"__term_{term}.txt"
            if term.upper() in self.RESERVED_NAMES
            else f"{term}.txt"
        )

        return self.folder / term[0].upper() / filename

    def query(self, term: str) -> list[dict]:
        path = self.term_path(term)

        if not path.exists():
            return []

        postings = []

        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                try:
                    book_id, frequency, raw_positions = line.strip().split(
                        ",", 2
                    )

                    postings.append(
                        validate_posting(
                            int(book_id),
                            int(frequency),
                            json.loads(raw_positions),
                        )
                    )

                except (ValueError, TypeError) as error:
                    raise ValueError(
                        f"Entrada invalida en {path}, linea {line_number}: "
                        f"{error}"
                    ) from error

        return sorted_postings(postings)


class SqliteIndexStore(InvertedIndexStore):
    def __init__(self, path: Path | str):
        self.path = Path(path)

        if not self.path.is_file():
            raise FileNotFoundError(
                f"No existe el indice SQLite: {self.path}"
            )

    def query(self, term: str) -> list[dict]:
        term = normalize_term(term)

        # mode=ro evita crear una base vacia por error.
        uri = self.path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)

        try:
            rows = connection.execute(
                """
                SELECT book_id, frequency, positions
                FROM inverted_index
                WHERE term = ?
                ORDER BY book_id
                """,
                (term,),
            ).fetchall()
        finally:
            connection.close()

        return sorted_postings([
            validate_posting(
                book_id,
                frequency,
                json.loads(raw_positions),
            )
            for book_id, frequency, raw_positions in rows
        ])
