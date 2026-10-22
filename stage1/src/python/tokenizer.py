import re
import unicodedata

STOP_WORDS_ES = {"el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "que", "de", "del", "en", "con", "por", "para", "su", "sus"}
STOP_WORDS_EN = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "from", "of", "is", "it", "that", "this"}

class MultilingualTokenizer:
    def __init__(self, stop_words=None):
        if stop_words is None:
            self.stop_words = STOP_WORDS_ES.union(STOP_WORDS_EN)
        else:
            self.stop_words = set(stop_words)

    def tokenize_with_positions(self, text: str) -> list:
        text = text.lower()
        tokens_with_pos = []
        for pos, match in enumerate(re.finditer(r'\b[^\W\d_]{3,}\b', text, re.UNICODE)):
            token = match.group()
            if token not in self.stop_words:
                tokens_with_pos.append((token, pos))
        return tokens_with_pos