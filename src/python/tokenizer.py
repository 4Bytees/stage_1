import re


STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
    "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
    "such", "that", "the", "their", "then", "there", "these", "they",
    "this", "to",
})

TOKEN_PATTERN = re.compile(r"\b[a-z]{3,}\b")


def tokenize_with_positions(text: str, stop_words=None) -> list[tuple[str, int]]:
    """
    Contrato provisional, compatible con el pipeline Python original:

    - Convertir a minusculas.
    - Considerar palabras ASCII de al menos tres caracteres.
    - Numerar esas palabras desde cero.
    - Eliminar stop-words sin renumerar las posiciones restantes.
    """
    excluded = STOP_WORDS if stop_words is None else frozenset(stop_words)

    return [
        (match.group(), position)
        for position, match in enumerate(TOKEN_PATTERN.finditer(text.lower()))
        if match.group() not in excluded
    ]


def tokenize(text: str) -> dict[str, list[int]]:
    positions_by_term = {}

    for term, position in tokenize_with_positions(text):
        positions_by_term.setdefault(term, []).append(position)

    return positions_by_term


class MultilingualTokenizer:
    """
    Interfaz conservada por compatibilidad.

    El nombre no implica soporte Unicode: utiliza el contrato ASCII
    provisional compartido con el pipeline.
    """

    def __init__(self, stop_words=None):
        self.stop_words = (
            STOP_WORDS if stop_words is None else frozenset(stop_words)
        )

    def tokenize_with_positions(self, text: str) -> list[tuple[str, int]]:
        return tokenize_with_positions(text, self.stop_words)