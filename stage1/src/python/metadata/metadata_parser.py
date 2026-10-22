import os
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATALAKE_TIME_DIR = BASE_DIR / "datalake" / "time"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
DATAMARTS_DIR = BASE_DIR / "datamarts"
DB_PATH = DATAMARTS_DIR / "metadata.db"
CONTROL_DIR = BASE_DIR / "control"
DOWNLOADS_FILE = CONTROL_DIR / "downloaded_books.txt"

def init_db():
    DATAMARTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT,
            language TEXT,
            file_path TEXT
        )
    """)
    conn.commit()
    conn.close()

def find_header_file(book_id: int) -> Path | None:
    target_files = [f"{book_id}.header.txt", f"{book_id}_header.txt"]
    
    DATALAKE_DIR = BASE_DIR / "datalake"
    if DATALAKE_DIR.exists():
        for root, _, files in os.walk(DATALAKE_DIR):
            for file in files:
                if file in target_files:
                    return Path(root) / file

    if SAMPLE_DATA_DIR.exists():
        for root, _, files in os.walk(SAMPLE_DATA_DIR):
            for file in files:
                if file in target_files:
                    return Path(root) / file

    return None

def parse_header(file_path: Path) -> dict:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    
    title_match = re.search(r"^Title:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    author_match = re.search(r"^Author:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    lang_match = re.search(r"^Language:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    
    return {
        "title": title_match.group(1).strip() if title_match else "Unknown",
        "author": author_match.group(1).strip() if author_match else "Unknown",
        "language": lang_match.group(1).strip() if lang_match else "Unknown"
    }

def process_single_metadata(book_id: int):
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT book_id FROM books WHERE book_id = ?", (book_id,))
    if cursor.fetchone():
        conn.close()
        return

    header_path = find_header_file(book_id)
    if header_path and header_path.exists():
        metadata = parse_header(header_path)
        cursor.execute("""
            INSERT INTO books (book_id, title, author, language, file_path)
            VALUES (?, ?, ?, ?, ?)
        """, (book_id, metadata["title"], metadata["author"], metadata["language"], str(header_path)))
        print(f"[METADATA] Successfully stored metadata for book ID {book_id}")
    else:
        print(f"[METADATA] Header file for book ID {book_id} not found in datalake/time/ or sample_data/")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("--- Starting Metadata Parser Execution ---")
    process_single_metadata(1)