import os

class ControlLayer:
    def __init__(self, crawler, metadata_service, indexer_service, control_dir="control"):
        self.crawler = crawler
        self.metadata_service = metadata_service
        self.indexer_service = indexer_service
        self.control_dir = control_dir
        
        self.downloaded_file = os.path.join(control_dir, "downloaded_books.txt")
        self.indexed_file = os.path.join(control_dir, "indexed_books.txt")
        
        os.makedirs(self.control_dir, exist_ok=True)
        self.downloaded_ids = self._load_ids(self.downloaded_file)
        self.indexed_ids = self._load_ids(self.indexed_file)

    def _load_ids(self, filepath):
        if not os.path.exists(filepath):
            return set()
        with open(filepath, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())

    def _mark_as_done(self, filepath, book_id, id_set):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{book_id}\n")
        id_set.add(str(book_id))

    def process_book(self, book_id):
        book_id_str = str(book_id)
        book_id_int = int(book_id)

        if book_id_str not in self.downloaded_ids:
            try:
                success = self.crawler.download(book_id_int)
            except Exception as e:
                if hasattr(self.crawler, "_crawl_book"):
                    success = self.crawler._crawl_book(book_id_int)
                elif hasattr(self.crawler, "download_and_store"):
                    success = self.crawler.download_and_store(book_id_int)
                else:
                    raise e

            if success or success is None:
                self._mark_as_done(self.downloaded_file, book_id_str, self.downloaded_ids)
            else:
                print(f"[Error] The book could not be downloaded {book_id_str}")
                return

        if book_id_str not in self.indexed_ids:
            if hasattr(self.metadata_service, 'process_single_metadata'):
                self.metadata_service.process_single_metadata(book_id_str)
            elif hasattr(self.metadata_service, 'metadata_parser'):
                self.metadata_service.metadata_parser(book_id_str)

            if hasattr(self.indexer_service, 'process_single_indexing'):
                self.indexer_service.process_single_indexing(book_id_str)
            elif hasattr(self.indexer_service, 'index_book'):
                self.indexer_service.index_book(book_id_str)

            self._mark_as_done(self.indexed_file, book_id_str, self.indexed_ids)