from datetime import datetime, timezone
from pathlib import Path

from storage.book_storage import BookStorage


class BookStorageDate(BookStorage):
    def __init__(self, datalake_path):
        super().__init__(Path(datalake_path))

    def save(self, book_id, content):
        content_separated = super().separate_header(content)

        if not content_separated:
            return False

        header_content, body_content = content_separated

        path = self.get_book_path()
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

    def get_book_path(self):
        now = datetime.now(timezone.utc)

        current_date = now.strftime("%Y%m%d")
        current_hour = now.strftime("%H")

        root = Path(self.datalake_path)

        # Acepta tanto datalake/ como datalake/time/
        if root.name.lower() != "time":
            root = root / "time"

        time_dir = root / current_date / current_hour
        time_dir.mkdir(parents=True, exist_ok=True)

        return time_dir