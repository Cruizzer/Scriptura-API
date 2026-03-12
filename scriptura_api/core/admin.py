from django.contrib import admin
from .models import Book, Chapter, Verse, Section, Footnote, Collection


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    show_change_link = True


class VerseInline(admin.TabularInline):
    model = Verse
    extra = 0
    fields = ['number', 'paragraph_start', 'text']


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ['start_verse', 'title']


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
    inlines = [SectionInline, VerseInline]

    def verse_count(self, obj):
        return obj.verses.count()
    verse_count.short_description = 'Verses'


@admin.register(Verse)
class VerseAdmin(admin.ModelAdmin):
    list_display = ['id', 'chapter', 'number', 'paragraph_start', 'text_preview']
    list_filter = ['chapter__book__testament', 'chapter__book']
    search_fields = ['text', 'chapter__book__name']

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text'


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'chapter', 'start_verse', 'title']
    list_filter = ['chapter__book', 'chapter__book__testament']
    search_fields = ['title', 'chapter__book__name']


@admin.register(Footnote)
class FootnoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'verse', 'marker', 'text_preview']
    list_filter = ['verse__chapter__book', 'verse__chapter__book__testament']
    search_fields = ['text', 'verse__chapter__book__name']

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Footnote'


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'is_public', 'verse_count', 'created_at', 'updated_at']
    list_filter = ['user', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'user__username', 'user__email']
    filter_horizontal = ['verses']
    readonly_fields = ['created_at', 'updated_at']

    def is_public(self, obj):
        return obj.user is None
    is_public.boolean = True
    is_public.short_description = 'Public'

    def verse_count(self, obj):
        return obj.verses.count()
    verse_count.short_description = 'Verses'
