from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from analytics.services.text_analytics import TextAnalyticsService
from core.models import Book, Chapter, Verse, Collection
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
        resp = self.client.get(reverse('theme-analytics', args=[theme.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['theme'], "Greeting")
        # at least one book should report keyword count >=1
        counts = [c['keyword_count'] for c in data['occurrences']]
        self.assertTrue(any(c >= 1 for c in counts))


class CollectionAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.owner = User.objects.create_user(username='owner', password='pw123')
        self.other_user = User.objects.create_user(username='other', password='pw123')

        book = Book.objects.create(name="Genesis", testament="OT")
        chapter = Chapter.objects.create(book=book, number=1)
        verse = Verse.objects.create(chapter=chapter, number=1, text="In the beginning")

        self.public_collection = Collection.objects.create(
            user=self.owner,
            name='Public collection',
            is_public=True,
        )
        self.public_collection.verses.add(verse)

        self.private_collection = Collection.objects.create(
            user=self.owner,
            name='Private collection',
            is_public=False,
        )
        self.private_collection.verses.add(verse)

    def test_unauthenticated_list_shows_only_public_collections(self):
        response = self.client.get(reverse('collection-list'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = [item['name'] for item in payload['results']]

        self.assertIn(self.public_collection.name, names)
        self.assertNotIn(self.private_collection.name, names)

    def test_owner_can_see_private_collection_in_list(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('collection-list'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = [item['name'] for item in payload['results']]

        self.assertIn(self.public_collection.name, names)
        self.assertIn(self.private_collection.name, names)

    def test_non_owner_cannot_retrieve_private_collection(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('collection-detail', args=[self.private_collection.id]))
        self.assertEqual(response.status_code, 404)

    def test_create_collection_assigns_authenticated_owner(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse('collection-list'),
            {
                'name': 'Created by API',
                'description': 'owned by current user',
                'is_public': False,
                'verses': [],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        created = Collection.objects.get(name='Created by API')
        self.assertEqual(created.user_id, self.owner.id)
