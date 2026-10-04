import requests

class GutenbergRequest:
    base_url = "https://www.gutenberg.org/cache/epub"

    def get_url(self, book_id):
        return f"{self.base_url}/{book_id}/pg{book_id}.txt"

    def fetch_book(self, book_id):
        try:
            response = requests.get(self.get_url(book_id), timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"[ERROR] Connection failed for the book {book_id}: {e}")
        return None