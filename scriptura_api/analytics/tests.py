from django.test import TestCase
from core.models import Book, Chapter, Verse
from .models import BookSummary
from .services.text_analytics import TextAnalyticsService


class BookSummaryTests(TestCase):
    def setUp(self):
        book = Book.objects.create(name="Alpha", testament="Old")
        chap = Chapter.objects.create(book=book, number=1)
        Verse.objects.create(chapter=chap, number=1, text="one two")
        Verse.objects.create(chapter=chap, number=2, text="two three")
        # simulate ingestion logic
        text = "one two two three"
        self.summary = BookSummary.objects.create(
            book=book,
            word_count=TextAnalyticsService.word_count(text),
            entropy=TextAnalyticsService.entropy(text),
            ttr=TextAnalyticsService.type_token_ratio(text),
            hapax_count=TextAnalyticsService.hapax_legomena(text),
        )

    def test_summary_values(self):
        self.assertEqual(self.summary.word_count, 4)
        self.assertEqual(self.summary.hapax_count, 2)
        self.assertGreater(self.summary.entropy, 0)
