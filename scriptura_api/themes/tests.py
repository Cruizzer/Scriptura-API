from django.test import TestCase
from rest_framework.test import APIClient

from .models import Theme, ThemeKeyword


class ThemeApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()

	def test_create_theme_with_keywords(self):
		response = self.client.post(
			'/api/themes/',
			{
				'name': 'Covenant',
				'keywords': ['promise', {'word': 'oath'}],
			},
			format='json',
		)

		self.assertEqual(response.status_code, 201)
		theme = Theme.objects.get(name='Covenant')
		words = set(theme.keywords.values_list('word', flat=True))
		self.assertEqual(words, {'promise', 'oath'})

	def test_retrieve_theme_includes_keywords_and_occurrences_endpoint(self):
		theme = Theme.objects.create(name='Faith')
		ThemeKeyword.objects.create(theme=theme, word='belief')
		ThemeKeyword.objects.create(theme=theme, word='trust')

		response = self.client.get(f'/api/themes/{theme.id}/')
		self.assertEqual(response.status_code, 200)

		payload = response.json()
		self.assertEqual(payload['name'], 'Faith')
		self.assertEqual(len(payload['keywords']), 2)
		self.assertEqual(payload['occurrences_endpoint'], f'/api/analytics/themes/{theme.id}/')

	def test_deleting_theme_cascades_keywords(self):
		theme = Theme.objects.create(name='Hope')
		ThemeKeyword.objects.create(theme=theme, word='expectation')

		response = self.client.delete(f'/api/themes/{theme.id}/')
		self.assertEqual(response.status_code, 204)
		self.assertFalse(Theme.objects.filter(id=theme.id).exists())
		self.assertEqual(ThemeKeyword.objects.count(), 0)
