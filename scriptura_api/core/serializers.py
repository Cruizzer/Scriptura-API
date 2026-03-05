from rest_framework import serializers
from .models import Book, Chapter, Verse, Section, Footnote, Collection


class FootnoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Footnote
        fields = ['id', 'marker', 'text']


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'start_verse', 'title']


class VerseSerializer(serializers.ModelSerializer):
    book_name = serializers.CharField(source='chapter.book.name', read_only=True)
    chapter_number = serializers.IntegerField(source='chapter.number', read_only=True)
    footnotes = FootnoteSerializer(many=True, read_only=True)
    section_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Verse
        fields = [
            'id',
            'number',
            'text',
            'paragraph_start',
            'book_name',
            'chapter_number',
            'section_title',
            'footnotes',
        ]

    def get_section_title(self, obj):
        section_map = self.context.get('section_map', {})
        return section_map.get(obj.number)


class ChapterListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for chapter lists - no verses included."""
    book_name = serializers.CharField(source='book.name', read_only=True)
    chapter_number = serializers.IntegerField(source='number')
    verse_count = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'book_name', 'chapter_number', 'verse_count']

    def get_verse_count(self, obj):
        return obj.verses.count()


class ChapterSerializer(serializers.ModelSerializer):
    """Full chapter serializer with all verses for detail view."""
    verses = serializers.SerializerMethodField()
    sections = SectionSerializer(many=True, read_only=True)
    book_name = serializers.CharField(source='book.name', read_only=True)
    chapter_number = serializers.IntegerField(source='number')

    class Meta:
        model = Chapter
        fields = ['id', 'book_name', 'chapter_number', 'sections', 'verses']

    def get_verses(self, obj):
        section_map = {s.start_verse: s.title for s in obj.sections.all()}
        verses = obj.verses.all().order_by('number')
        return VerseSerializer(
            verses,
            many=True,
            context={**self.context, 'section_map': section_map}
        ).data


class BookSerializer(serializers.ModelSerializer):
    chapter_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ['id', 'name', 'testament', 'chapter_count']

    def get_chapter_count(self, obj):
        return obj.chapters.count()


class BookDetailSerializer(serializers.ModelSerializer):
    """Full book detail - use ChapterListSerializer to avoid loading all verses."""
    chapters = ChapterListSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'name', 'testament', 'chapters']


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for user-curated verse collections."""
    verse_count = serializers.SerializerMethodField()
    theme_count = serializers.SerializerMethodField()
    verses = VerseSerializer(many=True, read_only=True)
    themes = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'verses', 'themes', 'verse_count', 'theme_count', 'created_at', 'updated_at']

    def get_verse_count(self, obj):
        return obj.verses.count()

    def get_theme_count(self, obj):
        return obj.themes.count()


class CollectionWriteSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating/updating collections."""
    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'verses', 'themes', 'created_at', 'updated_at']