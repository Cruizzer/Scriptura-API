from django.db import models

# ---------------------------------------------------------------------------
# Testament choices — covers Protestant (OT/NT), Catholic (adds DC),
# and leaves room for other canons.
# ---------------------------------------------------------------------------
TESTAMENT_CHOICES = [
    ("OT", "Old Testament"),
    ("NT", "New Testament"),
    ("DC", "Deuterocanonical"),   # Tobit, Judith, 1-2 Macc, Wis, Sir, Bar + additions
]

# Douay-Rheims deuterocanonical books (7 books + additions to Esther & Daniel)
DEUTEROCANONICAL_BOOKS = [
    "Tobit",
    "Judith",
    "1 Maccabees",
    "2 Maccabees",
    "Wisdom",
    "Sirach",          # also called Ecclesiasticus in DR
    "Baruch",          # includes Letter of Jeremiah as chapter 6 in DR
]

# Canonical order for all 73 DR books (OT + DC interspersed as in DR canon)
DOUAY_RHEIMS_CANON = [
    # Pentateuch
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    # Historical
    "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles",
    "Ezra", "Nehemiah",
    "Tobit", "Judith", "Esther",
    "1 Maccabees", "2 Maccabees",
    # Wisdom / Poetical
    "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Wisdom", "Sirach",
    # Prophets
    "Isaiah", "Jeremiah", "Lamentations", "Baruch",
    "Ezekiel", "Daniel",
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    # New Testament
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James",
    "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John",
    "Jude", "Revelation",
]


class BookSummary(models.Model):
    book = models.OneToOneField(
        'core.Book',
        related_name='summary',
        on_delete=models.CASCADE,
    )
    word_count = models.PositiveIntegerField(default=0)
    entropy = models.FloatField(null=True, blank=True)
    ttr = models.FloatField(null=True, blank=True)
    hapax_count = models.PositiveIntegerField(null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary for {self.book.name}"


class ThemeCoverageCache(models.Model):
    """Cached per-theme coverage payload used by ThemeAnalyticsView."""

    theme = models.OneToOneField(
        'themes.Theme',
        related_name='coverage_cache',
        on_delete=models.CASCADE,
    )
    keyword_signature = models.CharField(max_length=64)
    coverage = models.JSONField(default=list)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Coverage cache for {self.theme.name}"


class SimilarityCache(models.Model):
    """
    Cached similarity graph payload.

    The graph is expensive to compute (O(n²) over all verses in the DB).
    We cache the last result keyed on metric + threshold + a hash of the
    Book table so that the cache is invalidated automatically whenever books
    are added or removed (e.g. when deuterocanonical books are ingested).

    book_set_hash  — sha256 of the sorted list of book PKs in the DB.
    metric         — "cosine", "jaccard", or "tfidf_cosine".
    threshold      — similarity threshold used when the result was computed.
    graph_data     — the full JSON payload returned to the frontend.
    """

    book_set_hash = models.CharField(max_length=64)
    metric = models.CharField(max_length=32)
    threshold = models.FloatField()
    graph_data = models.JSONField(default=dict)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("book_set_hash", "metric", "threshold")]

    def __str__(self):
        return f"SimilarityCache metric={self.metric} threshold={self.threshold}"