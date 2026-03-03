from rest_framework import serializers
from .models import Book, Chapter, Verse


class VerseSerializer(serializers.ModelSerializer):
    book_name = serializers.CharField(source='chapter.book.name', read_only=True)
    chapter_number = serializers.IntegerField(source='chapter.number', read_only=True)
    
    class Meta:
        model = Verse
        fields = ['id', 'number', 'text', 'book_name', 'chapter_number']


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
    verses = VerseSerializer(many=True, read_only=True)
    book_name = serializers.CharField(source='book.name', read_only=True)
    chapter_number = serializers.IntegerField(source='number')

    class Meta:
        model = Chapter
        fields = ['id', 'book_name', 'chapter_number', 'verses']


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