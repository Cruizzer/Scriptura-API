from rest_framework import serializers
from .models import BookSummary


class BookSummarySerializer(serializers.ModelSerializer):
    book = serializers.CharField(source='book.name', read_only=True)

    class Meta:
        model = BookSummary
        fields = ['book', 'word_count', 'entropy', 'ttr', 'hapax_count', 'updated']
