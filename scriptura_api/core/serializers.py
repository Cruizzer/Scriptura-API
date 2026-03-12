from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
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

    @extend_schema_field(OpenApiTypes.STR)
    def get_section_title(self, obj) -> str:
        section_map = self.context.get('section_map', {})
        if section_map:
            return section_map.get(obj.number)

        # Fallback for endpoints that serialize Verse directly (e.g. /api/verses/)
        # where chapter-level section map is not passed via serializer context.
        prefetched = getattr(obj.chapter, '_prefetched_objects_cache', {}).get('sections')
        if prefetched is not None:
            for section in prefetched:
                if section.start_verse == obj.number:
                    return section.title
            return None

        section = obj.chapter.sections.filter(start_verse=obj.number).only('title').first()
        return section.title if section else None


class ChapterListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for chapter lists - no verses included."""
    book_name = serializers.CharField(source='book.name', read_only=True)
    chapter_number = serializers.IntegerField(source='number')
    verse_count = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'book_name', 'chapter_number', 'verse_count']

    @extend_schema_field(OpenApiTypes.INT)
    def get_verse_count(self, obj) -> int:
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

    @extend_schema_field(VerseSerializer(many=True))
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

    @extend_schema_field(OpenApiTypes.INT)
    def get_chapter_count(self, obj) -> int:
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
    verses = VerseSerializer(many=True, read_only=True)
    user = serializers.IntegerField(source='user_id', read_only=True)
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'is_public', 'verses', 'verse_count', 'user', 'created_by_username', 'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.INT)
    def get_verse_count(self, obj) -> int:
        return obj.verses.count()

    @extend_schema_field(OpenApiTypes.STR)
    def get_created_by_username(self, obj) -> str:
        return obj.user.username if obj.user else None


class CollectionWriteSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating/updating collections."""
    verses = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Verse.objects.all(),
        required=False
    )
    user = serializers.IntegerField(source='user_id', read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'is_public', 'verses', 'user', 'created_at', 'updated_at']