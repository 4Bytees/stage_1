from pathlib import Path
from ..base_container import InvertedIndexDatamartContainer, DATALAKE_DIR, DATAMARTS_DIR

class HierarchicalFolderStructure(InvertedIndexDatamartContainer):

    def __init__(self, datalake_path=DATALAKE_DIR, output_folder=DATAMARTS_DIR / "inverted_index_folders"):
        super().__init__(datalake_path)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.reserved_names = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", 
            "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", 
            "LPT6", "LPT7", "LPT8", "LPT9"
        }

    def save_index_for_book(self, book_id: int, position_dict: dict):
        for word, positions in position_dict.items():
            if word.upper() in self.reserved_names:
                continue
            first_letter = word[0].upper()
            if not first_letter.isalpha():
                continue

            letter_dir = self.output_folder / first_letter
            letter_dir.mkdir(parents=True, exist_ok=True)

            term_file = letter_dir / f"{word}.txt"
            line = f"{book_id},{len(positions)},{positions}\n"

            with open(term_file, "a", encoding="utf-8") as f:
                f.write(line)