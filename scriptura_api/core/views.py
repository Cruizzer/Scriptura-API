from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Book
from .serializers import BookSerializer

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
    queryset = Book.objects.all().order_by('order')
    serializer_class = BookSerializer