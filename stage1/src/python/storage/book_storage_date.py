from datetime import datetime, timezone
from storage.book_storage import BookStorage

class BookStorageDate(BookStorage):
    def __init__(self, datalake_path):
        super().__init__(datalake_path)

    def save(self, book_id, content):
        content_separated = super().separate_header(content)

        if not content_separated:
            return False

        header_content, body_content = content_separated

        path = self.get_book_path()
        header_path = path / f"{book_id}_header.txt"
        body_path = path / f"{book_id}_body.txt"

        with open(header_path, "w", encoding="utf-8") as file:
            file.write(header_content.strip())
        with open(body_path, "w", encoding="utf-8") as file:
            file.write(body_content.strip())
            
        return str(header_path), str(body_path)

    def get_book_path(self):
        current_path = datetime.now(timezone.utc).strftime('%Y%m%d')
        current_time = datetime.now(timezone.utc).strftime('%H')

        time_dir = self.datalake_path / "time" / current_path / current_time

        time_dir.mkdir(parents=True, exist_ok=True)
        return time_dir