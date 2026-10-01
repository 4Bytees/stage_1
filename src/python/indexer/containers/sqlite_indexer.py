import json
import sqlite3
from pathlib import Path
from ..base_container import InvertedIndexDatamartContainer, DATALAKE_DIR, DATAMARTS_DIR

class SqliteIndexer(InvertedIndexDatamartContainer):
    """Tercera estructura de datamart: persistencia en base de datos indexada."""

    def __init__(self, datalake_path=DATALAKE_DIR, db_path=DATAMARTS_DIR / "inverted_index.db"):
        super().__init__(datalake_path)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inverted_index (
                    term TEXT,
                    book_id INTEGER,
                    frequency INTEGER,
                    positions TEXT,
                    PRIMARY KEY (term, book_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_term ON inverted_index(term)")
            conn.commit()

    def save_index_for_book(self, book_id: int, position_dict: dict):
        records = [
            (term, book_id, len(positions), json.dumps(positions))
            for term, positions in position_dict.items()
        ]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO inverted_index (term, book_id, frequency, positions)
                VALUES (?, ?, ?, ?)
            """, records)
            conn.commit()