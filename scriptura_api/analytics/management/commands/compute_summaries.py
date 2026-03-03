from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Book
from analytics.models import BookSummary
from analytics.services.text_analytics import TextAnalyticsService


class Command(BaseCommand):
    help = 'Compute analytics summaries for all books in the database'

    def handle(self, *args, **options):
        books = Book.objects.all()
        created_count = 0
        updated_count = 0

        self.stdout.write(f'Processing {books.count()} books...')

        with transaction.atomic():
            for book in books:
                # gather all text from this book
                verses = []
                for chapter in book.chapters.all():
                    for verse in chapter.verses.all():
                        verses.append(verse.text)

                full_text = " ".join(verses)

                # compute metrics
                summary_values = {
                    'word_count': TextAnalyticsService.word_count(full_text),
                    'entropy': TextAnalyticsService.entropy(full_text),
                    'ttr': TextAnalyticsService.type_token_ratio(full_text),
                    'hapax_count': TextAnalyticsService.hapax_legomena(full_text),
                }

                # create or update
                summary, created = BookSummary.objects.update_or_create(
                    book=book,
                    defaults=summary_values
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                self.stdout.write(f'  {book.name}: {summary_values["word_count"]} words')

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {created_count}, updated {updated_count} summaries.'
        ))
