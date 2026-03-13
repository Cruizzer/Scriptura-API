"""Simple repository layer isolating ORM queries for core models."""

from django.db.models import Count

from .models import Book, Chapter, Verse


class BookRepository:
    @staticmethod
    def all():
        return Book.objects.annotate(chapter_count=Count('chapters')).all()

    @staticmethod
    def by_testament(testament: str):
        return Book.objects.filter(testament__iexact=testament).annotate(chapter_count=Count('chapters'))

    @staticmethod
    def get(pk):
        return Book.objects.get(pk=pk)


class ChapterRepository:
    @staticmethod
    def all():
        return Chapter.objects.select_related('book').all()

    @staticmethod
    def by_book(book_id):
        return Chapter.objects.filter(book_id=book_id)


class VerseRepository:
    @staticmethod
    def all():
        return Verse.objects.select_related('chapter__book').prefetch_related('chapter__sections', 'footnotes').all()

    @staticmethod
    def search(text_contains: str):
        return Verse.objects.filter(text__icontains=text_contains)
