from abc import ABC, abstractmethod
from pathlib import Path
import os
import tempfile

from tokenizer import STOP_WORDS, tokenize as tokenize_text


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATALAKE_DIR = BASE_DIR / "datalake"
DATAMARTS_DIR = BASE_DIR / "datamarts"


def atomic_write_text(path: Path, content: str) -> None:
    """
    Escribe en un temporal del mismo directorio y sustituye el destino.

    La sustitucion afecta a un archivo, no al conjunto de datamarts.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, path)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class InvertedIndexDatamartContainer(ABC):
    def __init__(self, datalake_path=DATALAKE_DIR):
        self.datalake_path = Path(datalake_path)

    def tokenize(self, text: str) -> dict[str, list[int]]:
        return tokenize_text(text)

    @abstractmethod
    def save_index_for_book(
        self,
        book_id: int,
        position_dict: dict[str, list[int]],
    ):
        pass