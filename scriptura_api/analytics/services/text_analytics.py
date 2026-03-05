import re
import math
from collections import Counter

# ---------------------------------------------------------------------------
# Biblical stop words
# ---------------------------------------------------------------------------
# Standard English stop words PLUS high-frequency biblical function words that
# appear in virtually every book of the Douay-Rheims and therefore carry zero
# discriminating power for similarity analysis.  Without filtering these, the
# similarity matrix collapses: every book looks like every other book because
# they all share enormous counts of "the", "and", "lord", "said", "unto", etc.
#
# Criteria for inclusion here:
#   - Standard English function words (articles, prepositions, conjunctions,
#     pronouns, auxiliaries) that carry no thematic content.
#   - Biblical words whose document-frequency approaches 100 % across all 73
#     Douay-Rheims books (LORD/lord, God/god, said, unto, shall, thee, thou,
#     thy, ye, saith, hath, hast, doth).
#
# Words NOT removed even if common:
#   - Content nouns with real thematic signal when concentrated in a book
#     (e.g. "king", "priest", "temple", "covenant", "law", "wisdom").
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset = frozenset({
    # Standard English function words
    "a", "an", "the",
    "and", "but", "or", "nor", "for", "yet", "so",
    "if", "as", "at", "by", "in", "of", "on", "to", "up",
    "out", "into", "from", "with", "upon", "over", "under",
    "about", "after", "before", "between", "through", "against",
    "among", "within", "without", "than", "then", "when", "where",
    "while", "since", "until", "because", "though", "although",
    "this", "that", "these", "those", "it", "its",
    "he", "him", "his", "she", "her", "hers",
    "we", "us", "our", "ours",
    "they", "them", "their", "theirs",
    "who", "whom", "whose", "which", "what",
    "i", "me", "my", "mine",
    "you", "your", "yours",
    "be", "is", "are", "was", "were", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "will", "would", "may", "might", "must", "can", "could",
    "should", "shall", "ought",
    "not", "no", "nor",
    "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such",
    "only", "own", "same", "very",
    "just", "also", "too", "again", "further",
    "here", "there", "how", "why",
    "once", "now", "then",
    "s", "t",

    # Archaic Douay-Rheims English function words
    "thee", "thou", "thy", "thine",
    "ye", "yea", "nay",
    "hath", "hast", "doth", "dost", "wilt", "art",
    "shalt", "canst", "wouldst", "shouldst",
    "unto", "wherefore", "thereof", "therein", "thereupon",
    "whereby", "wherein", "whereof", "hereof", "herein",
    "afore", "aforetime",
    "lo", "behold",

    # Near-universal biblical content words (>= 95% of books)
    "lord", "god", "said", "saith",
    "came", "come", "gone", "went", "go",
    "made", "make", "given", "give",
    "say", "speak", "spoken", "word", "words",
    "man", "men",
    "day", "days",
    "hand", "hands",
    "called", "call",
    "time", "times",
    "great", "good",
    "like", "thus",
    "one", "two", "three",
    "first", "second",
    "every", "many", "much",
})


def tokenize(text: str) -> list:
    """Tokenise, lower-case, and remove stop words."""
    tokens = re.findall(r"\b\w+\b", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


class TextAnalyticsService:
    """Reusable methods for computing metrics on strings of scripture."""

    @classmethod
    def word_frequency(cls, text: str) -> Counter:
        tokens = tokenize(text)
        return Counter(tokens)

    @classmethod
    def word_count(cls, text: str) -> int:
        # Raw count (no stop-word filtering) for human-readable display
        return len(re.findall(r"\b\w+\b", text.lower()))

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
        return -sum((count / total) * math.log2(count / total) for count in freq.values())

    @classmethod
    def hapax_legomena(cls, text: str) -> int:
        freq = cls.word_frequency(text)
        return sum(1 for count in freq.values() if count == 1)