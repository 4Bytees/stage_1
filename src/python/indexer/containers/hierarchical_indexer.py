from pathlib import Path

from ..base_container import (
    InvertedIndexDatamartContainer,
    DATALAKE_DIR,
    DATAMARTS_DIR,
    atomic_write_text,
)


class HierarchicalFolderStructure(InvertedIndexDatamartContainer):
    RESERVED_NAMES = frozenset(
        {"CON", "PRN", "AUX", "NUL"}
        | {f"COM{i}" for i in range(1, 10)}
        | {f"LPT{i}" for i in range(1, 10)}
    )

    def __init__(
        self,
        datalake_path=DATALAKE_DIR,
        output_folder=DATAMARTS_DIR / "inverted_index_folders",
    ):
        super().__init__(datalake_path)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def term_path(self, term: str) -> Path:
        """
        Mantiene los nombres habituales y codifica los reservados.

        Ejemplo: con -> C/__term_con.txt
        """
        if not term or any(char not in "abcdefghijklmnopqrstuvwxyz" for char in term):
            raise ValueError(f"Termino no valido para este contrato: {term!r}")

        filename = (
            f"__term_{term}.txt"
            if term.upper() in self.RESERVED_NAMES
            else f"{term}.txt"
        )

        return self.output_folder / term[0].upper() / filename

    def _read_other_books(self, path: Path, book_id: int) -> list[str]:
        """
        Conserva las lineas de otros libros.

        Retira todas las apariciones del libro actual, incluidas
        las duplicadas que pudiera haber dejado el antiguo append.
        """
        if not path.exists():
            return []

        remaining = []

        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue

            fields = line.split(",", 2)

            if len(fields) != 3:
                raise ValueError(
                    f"Entrada invalida en {path}, linea {line_number}"
                )

            try:
                existing_book_id = int(fields[0].strip())
            except ValueError as error:
                raise ValueError(
                    f"ID invalido en {path}, linea {line_number}"
                ) from error

            if existing_book_id != book_id:
                remaining.append(line)

        return remaining

    def save_index_for_book(
        self,
        book_id: int,
        position_dict: dict[str, list[int]],
    ):
        # Validar todos los terminos antes de empezar a escribir.
        new_entries = {
            self.term_path(term): positions
            for term, positions in position_dict.items()
        }

        # Tambien revisar terminos antiguos que ya no aparecen.
        paths = set(self.output_folder.rglob("*.txt"))
        paths.update(new_entries)

        for path in sorted(paths):
            remaining = self._read_other_books(path, book_id)

            if path in new_entries:
                positions = new_entries[path]
                remaining.append(
                    f"{book_id},{len(positions)},{positions}"
                )

            if remaining:
                atomic_write_text(path, "\n".join(remaining) + "\n")
            else:
                path.unlink(missing_ok=True)
