from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from core.models import Book, Chapter, Verse
from themes.models import Theme
from .models import BookSummary, ThemeCoverageCache
from .services.text_analytics import TextAnalyticsService


class BookSummaryTests(TestCase):
    def setUp(self):
        book = Book.objects.create(name="Alpha", testament="Old")
        chap = Chapter.objects.create(book=book, number=1)
        Verse.objects.create(chapter=chap, number=1, text="alpha beta")
        Verse.objects.create(chapter=chap, number=2, text="beta gamma")
        # simulate ingestion logic
        text = "alpha beta beta gamma"
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


class ThemeCoverageCacheTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        book = Book.objects.create(name="Alpha", testament="Old")
        chapter = Chapter.objects.create(book=book, number=1)
        Verse.objects.create(chapter=chapter, number=1, text="light and hope")
        Verse.objects.create(chapter=chapter, number=2, text="hope in darkness")

        self.theme = Theme.objects.create(name="Hope")
        self.theme.keywords.create(word="hope")

    def test_coverage_is_cached_in_db(self):
        url = reverse('theme-coverage', args=[self.theme.pk])

        first = self.client.get(url)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(ThemeCoverageCache.objects.count(), 1)

        cache = ThemeCoverageCache.objects.get(theme=self.theme)
        self.assertEqual(cache.coverage, first.json()['coverage'])

        second = self.client.get(url)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ThemeCoverageCache.objects.count(), 1)
        self.assertEqual(second.json()['coverage'], first.json()['coverage'])

    def test_cache_refreshes_when_keywords_change(self):
        url = reverse('theme-coverage', args=[self.theme.pk])

        first = self.client.get(url)
        first_coverage = first.json()['coverage']

        self.theme.keywords.create(word='light')

        second = self.client.get(url)
        second_coverage = second.json()['coverage']

        self.assertNotEqual(second_coverage, first_coverage)
