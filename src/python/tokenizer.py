import re
import unicodedata

# Lista base de stop words comunes (ampliable dinámicamente)
STOP_WORDS_ES = {"el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "que", "de", "del", "en", "con", "por", "para", "su", "sus"}
STOP_WORDS_EN = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "from", "of", "is", "it", "that", "this"}

class MultilingualTokenizer:
    def __init__(self, stop_words=None):
        if stop_words is None:
            self.stop_words = STOP_WORDS_ES.union(STOP_WORDS_EN)
        else:
            self.stop_words = set(stop_words)

    def tokenize(self, text: str) -> list:
        """
        Normaliza el texto a minúsculas, preserva caracteres alfabéticos Unicode
        (incluyendo tildes/ñ) y filtra stop words.
        """
        text = text.lower()
        # Mantiene letras Unicode (incluye diacríticos)
        tokens = re.findall(r'\b[^\W\d_]{3,}\b', text, re.UNICODE)
        return [token for token in tokens if token not in self.stop_words]