import json
import sqlite3
from pathlib import Path

from ..base_container import (
    InvertedIndexDatamartContainer,
    DATALAKE_DIR,
    DATAMARTS_DIR,
)


class SqliteIndexer(InvertedIndexDatamartContainer):
    def __init__(
        self,
        datalake_path=DATALAKE_DIR,
        db_path=DATAMARTS_DIR / "inverted_index.db",
    ):
        super().__init__(datalake_path)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        connection = sqlite3.connect(self.db_path)

        try:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS inverted_index (
                        term TEXT,
                        book_id INTEGER,
                        frequency INTEGER,
                        positions TEXT,
                        PRIMARY KEY (term, book_id)
                    )
                """)

                connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_book_id
                    ON inverted_index(book_id)
                """)
        finally:
            connection.close()

    def save_index_for_book(
        self,
        book_id: int,
        position_dict: dict[str, list[int]],
    ):
        records = [
            (
                term,
                book_id,
                len(positions),
                json.dumps(positions),
            )
            for term, positions in position_dict.items()
        ]

        connection = sqlite3.connect(self.db_path)

        try:
            # Borrado e insercion forman una unica transaccion.
            with connection:
                connection.execute(
                    "DELETE FROM inverted_index WHERE book_id = ?",
                    (book_id,),
                )

                connection.executemany("""
                    INSERT INTO inverted_index (
                        term, book_id, frequency, positions
                    )
                    VALUES (?, ?, ?, ?)
                """, records)
        finally:
            connection.close()