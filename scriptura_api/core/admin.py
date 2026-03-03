from django.contrib import admin
from .models import Book, Chapter, Verse


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    show_change_link = True


class VerseInline(admin.TabularInline):
    model = Verse
    extra = 0
    fields = ['number', 'text']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'testament', 'chapter_count']
    list_filter = ['testament']
    search_fields = ['name']
    inlines = [ChapterInline]

    def chapter_count(self, obj):
        return obj.chapters.count()
    chapter_count.short_description = 'Chapters'


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['id', 'book', 'number', 'verse_count']
    list_filter = ['book__testament', 'book']
    search_fields = ['book__name']
    inlines = [VerseInline]

    def verse_count(self, obj):
        return obj.verses.count()
    verse_count.short_description = 'Verses'


@admin.register(Verse)
class VerseAdmin(admin.ModelAdmin):
    list_display = ['id', 'chapter', 'number', 'text_preview']
    list_filter = ['chapter__book__testament', 'chapter__book']
    search_fields = ['text', 'chapter__book__name']

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text'
