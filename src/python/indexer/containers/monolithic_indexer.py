import json
from pathlib import Path

from ..base_container import (
    InvertedIndexDatamartContainer,
    DATALAKE_DIR,
    DATAMARTS_DIR,
    atomic_write_text,
)


class MonolithicIndexer(InvertedIndexDatamartContainer):
    def __init__(
        self,
        datalake_path=DATALAKE_DIR,
        output_path=DATAMARTS_DIR / "inverted_index.json",
    ):
        super().__init__(datalake_path)
        self.output_path = Path(output_path)

    def _load_index(self) -> dict:
        if not self.output_path.exists():
            return {}

        with self.output_path.open("r", encoding="utf-8") as file:
            index = json.load(file)

        if not isinstance(index, dict):
            raise ValueError("The JSON index must contain an object.")

        for term, postings in index.items():
            if not isinstance(postings, dict):
                raise ValueError(
                    f"Entries for the term{term!r} they are not an object."
                )

        return index

    def save_index_for_book(
        self,
        book_id: int,
        position_dict: dict[str, list[int]],
    ):
        index = self._load_index()
        book_key = str(book_id)

        for term in list(index):
            index[term].pop(book_key, None)

            if not index[term]:
                del index[term]

        for term, positions in position_dict.items():
            index.setdefault(term, {})[book_key] = {
                "frequency": len(positions),
                "positions": positions,
            }

        content = json.dumps(
            index,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )

        atomic_write_text(self.output_path, content + "\n")