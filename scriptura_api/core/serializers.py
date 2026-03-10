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
    user = serializers.IntegerField(source='user_id', read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'verses', 'themes', 'verse_count', 'theme_count', 'user', 'created_at', 'updated_at']

    def get_verse_count(self, obj):
        return obj.verses.count()

    def get_theme_count(self, obj):
        return obj.themes.count()


class CollectionWriteSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating/updating collections."""
    verses = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Verse.objects.all(),
        required=False
    )
    themes = serializers.SerializerMethodField(read_only=False)
    user = serializers.IntegerField(source='user_id', read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'verses', 'themes', 'user', 'created_at', 'updated_at']

    def get_themes(self, obj):
        return list(obj.themes.values_list('id', flat=True))
    
    def to_internal_value(self, data):
        # Handle themes as a list of IDs
        if 'themes' in data and isinstance(data['themes'], list):
            theme_ids = data['themes']
            # Keep themes in data as-is for now, we'll handle it in create/update
            from themes.models import Theme
            themes = Theme.objects.filter(id__in=theme_ids)
            if len(themes) != len(set(theme_ids)):
                self.fail('invalid', 'One or more theme IDs do not exist.')
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        themes = self.initial_data.get('themes', [])
        instance = super().create(validated_data)
        if themes:
            from themes.models import Theme
            theme_ids = [t if isinstance(t, int) else t.id for t in themes]
            instance.themes.set(Theme.objects.filter(id__in=theme_ids))
        return instance
    
    def update(self, instance, validated_data):
        themes = self.initial_data.get('themes')
        instance = super().update(instance, validated_data)
        if themes is not None:
            from themes.models import Theme
            theme_ids = [t if isinstance(t, int) else t.id for t in themes]
            instance.themes.set(Theme.objects.filter(id__in=theme_ids))
        return instance