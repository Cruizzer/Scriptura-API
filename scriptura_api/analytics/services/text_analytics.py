import re
import math
from collections import Counter


def tokenize(text: str) -> list[str]:
    """Very simple word tokenizer. Lower‑cases and keeps alphanumeric words."""
    return re.findall(r"\b\w+\b", text.lower())


class TextAnalyticsService:
    """Reusable methods for computing metrics on strings of scripture."""

    @classmethod
    def word_frequency(cls, text: str) -> Counter:
        tokens = tokenize(text)
        return Counter(tokens)

    @classmethod
    def word_count(cls, text: str) -> int:
        return len(tokenize(text))

    @classmethod
    def type_token_ratio(cls, text: str) -> float:
        tokens = tokenize(text)
        if not tokens:
            return 0.0
        return len(set(tokens)) / len(tokens)

    @classmethod
    def entropy(cls, text: str) -> float:
        freq = cls.word_frequency(text)
        total = sum(freq.values())
        if total == 0:
            return 0.0
        # Shannon entropy in bits
        return -sum((count / total) * math.log2(count / total) for count in freq.values())

    @classmethod
    def hapax_legomena(cls, text: str) -> int:
        freq = cls.word_frequency(text)
        return sum(1 for count in freq.values() if count == 1)
