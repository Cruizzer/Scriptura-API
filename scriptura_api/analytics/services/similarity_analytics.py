"""
Lexical similarity analytics for biblical books.

Algorithm: TF-IDF Cosine Similarity (default) with optional Jaccard fallback.

Why TF-IDF over raw cosine for scripture:
  Raw term-frequency cosine similarity is dominated by high-frequency words
  that appear in every book (even after stop-word filtering, words like
  "king", "israel", "covenant" still appear in most books).  TF-IDF
  downweights these cross-book ubiquitous terms and upweights words that
  are concentrated in only a few books, which is exactly what reveals
  genuine thematic/genre clusters (e.g. the Pauline epistles clustering
  together on "justification", "grace", "faith"; the Wisdom books on
  "wisdom", "folly"; the Maccabean history on "antiochus", "hellenism").

  This is the standard approach used in computational biblical studies
  (see e.g. Brooke & McLay, "Textual Analysis of Biblical Texts", and
  the ETCBC / BHSA corpus work at Vrije Universiteit Amsterdam).

Stop words:
  The heavy lifting is done in text_analytics.tokenize(), which strips both
  English function words and near-universal biblical vocabulary.  See the
  comments in that module for the full rationale.
"""
import math
from collections import Counter
from hashlib import sha256
from typing import Dict, List, Tuple

from .text_analytics import tokenize


class SimilarityAnalyticsService:

    # ------------------------------------------------------------------
    # Internal vector helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_word_vector(text: str) -> Counter:
        """Raw term-frequency counter (stop words already removed by tokenize)."""
        return Counter(tokenize(text))

    @staticmethod
    def _build_tfidf_vectors(vectors: List[Counter]) -> List[Dict[str, float]]:
        """
        Convert raw TF counters to TF-IDF weighted dictionaries.

        Uses:
          TF  = sublinear scaling: 1 + log(tf)   (dampens runaway high-freq terms)
          IDF = smoothed:  log((N+1) / (df+1)) + 1  (avoids zero-IDF for ubiquitous terms)
        """
        n_docs = len(vectors)
        if n_docs == 0:
            return []

        df: Counter = Counter()
        for vec in vectors:
            for term in vec:
                df[term] += 1

        tfidf_list: List[Dict[str, float]] = []
        for vec in vectors:
            tfidf: Dict[str, float] = {}
            for term, tf in vec.items():
                if tf <= 0:
                    continue
                tf_w = 1.0 + math.log(tf)
                idf_w = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
                tfidf[term] = tf_w * idf_w
            tfidf_list.append(tfidf)

        return tfidf_list

    @staticmethod
    def _cosine_dict(v1: Dict[str, float], v2: Dict[str, float]) -> float:
        """Cosine similarity for sparse float dicts (intersection only for dot product)."""
        if not v1 or not v2:
            return 0.0
        common = set(v1) & set(v2)
        dot = sum(v1[t] * v2[t] for t in common)
        mag1 = math.sqrt(sum(x * x for x in v1.values()))
        mag2 = math.sqrt(sum(x * x for x in v2.values()))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    @staticmethod
    def _cosine_counter(v1: Counter, v2: Counter) -> float:
        """Cosine similarity for Counter objects."""
        if not v1 or not v2:
            return 0.0
        all_words = set(v1) | set(v2)
        dot = sum(v1.get(w, 0) * v2.get(w, 0) for w in all_words)
        mag1 = math.sqrt(sum(c * c for c in v1.values()))
        mag2 = math.sqrt(sum(c * c for c in v2.values()))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    @staticmethod
    def jaccard_similarity(v1: Counter, v2: Counter) -> float:
        """Jaccard similarity on vocabulary sets (ignores frequency)."""
        w1, w2 = set(v1), set(v2)
        if not w1 and not w2:
            return 1.0
        union = len(w1 | w2)
        return len(w1 & w2) / union if union else 0.0

    # ------------------------------------------------------------------
    # Book-level similarity matrix
    # ------------------------------------------------------------------

    @classmethod
    def compute_book_similarity_matrix(
        cls, books, metric: str = "tfidf_cosine"
    ) -> Tuple[List[str], List[str], List[List[float]]]:
        """
        Compute pairwise similarity between all books.

        Returns:
            (book_names, testament_list, similarity_matrix)
            where testament_list[i] is the testament of book_names[i].
        """
        book_names: List[str] = []
        testaments: List[str] = []
        raw_vectors: List[Counter] = []

        for book in books:
            full_text = " ".join(
                v.text for c in book.chapters.all() for v in c.verses.all()
            )
            raw_vectors.append(cls._get_word_vector(full_text))
            book_names.append(book.name)
            testaments.append(getattr(book, 'testament', 'OT'))

        n = len(raw_vectors)
        matrix: List[List[float]] = [[0.0] * n for _ in range(n)]

        metric_key = (metric or "tfidf_cosine").lower().replace("-", "_")

        if metric_key in {"tfidf", "tfidf_cosine"}:
            tfidf = cls._build_tfidf_vectors(raw_vectors)
            for i in range(n):
                matrix[i][i] = 1.0
                for j in range(i + 1, n):
                    s = cls._cosine_dict(tfidf[i], tfidf[j])
                    matrix[i][j] = matrix[j][i] = s
        elif metric_key == "jaccard":
            for i in range(n):
                matrix[i][i] = 1.0
                for j in range(i + 1, n):
                    s = cls.jaccard_similarity(raw_vectors[i], raw_vectors[j])
                    matrix[i][j] = matrix[j][i] = s
        else:  # plain cosine
            for i in range(n):
                matrix[i][i] = 1.0
                for j in range(i + 1, n):
                    s = cls._cosine_counter(raw_vectors[i], raw_vectors[j])
                    matrix[i][j] = matrix[j][i] = s

        return book_names, testaments, matrix

    # ------------------------------------------------------------------
    # Graph builder
    # ------------------------------------------------------------------

    @classmethod
    def build_similarity_graph(
        cls,
        books,
        similarity_threshold: float = 0.3,
        metric: str = "tfidf_cosine",
    ) -> Dict:
        """
        Build edges for the similarity network.

        Each edge represents a book pair whose similarity score meets or
        exceeds the threshold. Book metadata is available via /api/books/.
        """
        book_list = list(books)

        book_names, _, sim_matrix = cls.compute_book_similarity_matrix(
            book_list, metric=metric
        )

        edges = []
        for i in range(len(book_names)):
            for j in range(i + 1, len(book_names)):
                sim = sim_matrix[i][j]
                if sim >= similarity_threshold:
                    edges.append({
                        "source": book_names[i],
                        "target": book_names[j],
                        "weight": round(sim, 4),
                    })

        return {
            "edges": edges,
            "metric": metric,
            "threshold": similarity_threshold,
        }

    # ------------------------------------------------------------------
    # Cache key helper (used by views.py)
    # ------------------------------------------------------------------

    @staticmethod
    def book_set_hash(books) -> str:
        """Stable hash of the current book PKs — used to invalidate the cache."""
        pks = sorted(str(b.id) for b in books)
        return sha256("|".join(pks).encode()).hexdigest()

    # ------------------------------------------------------------------
    # Verse recommendations
    # ------------------------------------------------------------------

    @classmethod
    def find_similar_verses(cls, verse_text: str, verses, top_k: int = 5) -> List[Dict]:
        ref_vec = cls._get_word_vector(verse_text)
        scored = []
        for verse in verses:
            s = cls._cosine_counter(ref_vec, cls._get_word_vector(verse.text))
            scored.append((verse, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "id": v.id,
                "reference": f"{v.chapter.book.name} {v.chapter.number}:{v.number}",
                "text": v.text,
                "similarity": round(s, 4),
            }
            for v, s in scored[:top_k]
        ]