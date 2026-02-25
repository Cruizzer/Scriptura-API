from rest_framework import serializers
from .models import Book, Chapter, Verse

class VerseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Verse
        fields = ['id', 'chapter', 'number', 'text']

class ChapterSerializer(serializers.ModelSerializer):
    verses = VerseSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'book', 'number', 'verses']

class BookSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'name', 'testament', 'order', 'chapters']