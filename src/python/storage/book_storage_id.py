from pathlib import Path

from storage.book_storage import BookStorage


class BookStorageId(BookStorage):
    def __init__(self, datalake_path):
        root = Path(datalake_path)

        if root.name.lower() != "id":
            root = root / "id"

        super().__init__(root)

    def save(self, book_id, content):
        book_id = int(book_id)
        content_separated = super().separate_header(content)

        if not content_separated:
            return False

        header_content, body_content = content_separated

        path = self.get_book_path(book_id)
        header_path = path / f"{book_id}_header.txt"
        body_path = path / f"{book_id}_body.txt"

        header_path.write_text(
            header_content.strip(),
            encoding="utf-8",
        )

        body_path.write_text(
            body_content.strip(),
            encoding="utf-8",
        )

        return str(header_path), str(body_path)

    def get_book_path(self, book_id):
        book_id = int(book_id)

        if book_id < 0:
            raise ValueError("The book ID cannot be negative.")

        book_id_str = f"{book_id:04d}"

        if len(book_id_str) % 2 != 0:
            book_id_str = "0" + book_id_str

        parts = [
            book_id_str[index:index + 2]
            for index in range(0, len(book_id_str), 2)
        ]

        path = Path(self.datalake_path)

        for part in parts:
            path = path / part

        path.mkdir(parents=True, exist_ok=True)
        return path