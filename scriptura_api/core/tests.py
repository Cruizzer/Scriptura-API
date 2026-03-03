from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from analytics.services.text_analytics import TextAnalyticsService
from core.models import Book, Chapter, Verse
from themes.models import Theme


class TextAnalyticsServiceTests(TestCase):
    def test_basic_metrics(self):
        text = "foo bar foo baz"
        self.assertEqual(TextAnalyticsService.word_count(text), 4)
        self.assertAlmostEqual(TextAnalyticsService.type_token_ratio(text), 0.75)
        # entropy should be positive
        self.assertGreater(TextAnalyticsService.entropy(text), 0)
        self.assertEqual(TextAnalyticsService.hapax_legomena(text), 2)


class APISmokeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # minimal data set: 1 book, 1 chapter, 2 verses
        self.book = Book.objects.create(name="Test book", testament="Old")
        chap = Chapter.objects.create(book=self.book, number=1)
        Verse.objects.create(chapter=chap, number=1, text="hello world")
        Verse.objects.create(chapter=chap, number=2, text="hello again")

    def test_book_list(self):
        resp = self.client.get(reverse('book-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.json()) >= 1)

    def test_verse_search(self):
        resp = self.client.get(reverse('verse-list'), {'contains': 'hello'})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertGreaterEqual(len(body['results']), 2)

    def test_theme_coverage(self):
        # create theme and keyword matching one verse
        theme = Theme.objects.create(name="Greeting")
        theme.keywords.create(word="hello")
        resp = self.client.get(reverse('theme-coverage', args=[theme.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['theme'], "Greeting")
        # at least one book should report keyword count >=1
        counts = [c['keyword_count'] for c in data['coverage']]
        self.assertTrue(any(c >= 1 for c in counts))
