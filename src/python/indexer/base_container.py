from abc import ABC, abstractmethod
from pathlib import Path
import re

STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
    "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
    "such", "that", "the", "their", "then", "there", "these", "they", "this", "to"
})

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATALAKE_DIR = BASE_DIR / "datalake"
DATAMARTS_DIR = BASE_DIR / "datamarts"

class InvertedIndexDatamartContainer(ABC):

    def __init__(self, datalake_path=DATALAKE_DIR):
        self.datalake_path = Path(datalake_path)

    def tokenize(self, text: str) -> dict[str, list[int]]:
        """Extrae palabras alfabéticas >= 3 letras, minúsculas, elimina stop words y guarda sus posiciones."""
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        position_dict = {}
        for pos, word in enumerate(words):
            if word not in STOP_WORDS:
                position_dict.setdefault(word, []).append(pos)
        return position_dict

    @abstractmethod
    def save_index_for_book(self, book_id: int, position_dict: dict):
        pass