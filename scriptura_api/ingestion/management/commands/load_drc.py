import json
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Book, Chapter, Verse

# metrics service and summary model
from analytics.services.text_analytics import TextAnalyticsService
from analytics.models import BookSummary

class Command(BaseCommand):
    help = 'Load DRC Bible JSON into the database efficiently'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to drc.json file')

    def handle(self, *args, **options):
        file_path = options['file']

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        books_created = 0
        chapters_created = 0
        verses_created = 0

        with transaction.atomic():  # single transaction for speed
            for book_index, book_entry in enumerate(data["books"][:-5]):
                book_name = book_entry['name']

                # Assign testament based on index
                testament = 'Old' if book_index < 46 else 'New'

                book, created_book = Book.objects.get_or_create(
                    name=book_name,
                    defaults={'testament': testament}
                )
                if created_book:
                    books_created += 1

                cumulative_text = []
                for chapter_entry in book_entry['chapters']:
                    chapter_number = chapter_entry['chapter']
                    chapter, created_chap = Chapter.objects.get_or_create(
                        book=book,
                        number=chapter_number
                    )
                    if created_chap:
                        chapters_created += 1

                    # Prepare all verses for bulk_create
                    verses_to_create = []
                    for verse_entry in chapter_entry['verses']:
                        verse_number = verse_entry['verse']
                        text = verse_entry['text']
                        verses_to_create.append(
                            Verse(chapter=chapter, number=verse_number, text=text)
                        )
                        cumulative_text.append(text)
                    Verse.objects.bulk_create(verses_to_create)
                    verses_created += len(verses_to_create)

                # after book insertion compute a summary
                full_text = " ".join(cumulative_text)
                summary_values = {
                    'word_count': TextAnalyticsService.word_count(full_text),
                    'entropy': TextAnalyticsService.entropy(full_text),
                    'ttr': TextAnalyticsService.type_token_ratio(full_text),
                    'hapax_count': TextAnalyticsService.hapax_legomena(full_text),
                }
                BookSummary.objects.update_or_create(
                    book=book,
                    defaults=summary_values
                )

        self.stdout.write(self.style.SUCCESS(
            f'Imported {books_created} books, {chapters_created} chapters, {verses_created} verses'
        ))