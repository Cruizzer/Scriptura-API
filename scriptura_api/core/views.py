from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Book, Chapter, Verse
from .serializers import (
    BookSerializer,
    BookDetailSerializer,
    ChapterSerializer,
    VerseSerializer
)

class BookAnalyticsView(APIView):
    def get(self, request, pk):
        book = Book.objects.get(pk=pk)
        
        # Aggregate all verse texts in the book
        text = " ".join(v.text for c in book.chapters.all() for v in c.verses.all())
        word_count = len(text.split())
        return Response({
            "book": book.name,
            "word_count": word_count
        })


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookDetailSerializer
        return BookSerializer
    

class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer


class VerseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Verse.objects.all()
    serializer_class = VerseSerializer