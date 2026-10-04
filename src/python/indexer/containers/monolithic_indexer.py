import json
from pathlib import Path
from ..base_container import InvertedIndexDatamartContainer, DATALAKE_DIR, DATAMARTS_DIR

class MonolithicIndexer(InvertedIndexDatamartContainer):

    def __init__(self, datalake_path=DATALAKE_DIR, output_path=DATAMARTS_DIR / "inverted_index.json"):
        super().__init__(datalake_path)
        self.output_path = Path(output_path)

    def save_index_for_book(self, book_id: int, position_dict: dict):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        existing_index = {}

        if self.output_path.exists():
            try:
                with open(self.output_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        existing_index = data
            except json.JSONDecodeError:
                existing_index = {}

        for word, positions in position_dict.items():
            if word not in existing_index or not isinstance(existing_index[word], dict):
                existing_index[word] = {}
            existing_index[word][str(book_id)] = {
                "frequency": len(positions),
                "positions": positions
            }

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(existing_index, f, indent=2)