from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import BookSummary
from .serializers import BookSummarySerializer

from themes.models import Theme
from core.models import Book
from analytics.services.text_analytics import TextAnalyticsService


# Create your views here.


class BookSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to precomputed analytics summaries."""
    queryset = BookSummary.objects.select_related('book').all()
    serializer_class = BookSummarySerializer

    # Example of a nested analytics endpoint /books/{pk}/details/
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Return raw values and possibly derived metrics."""
        summary = self.get_object()
        return Response(BookSummarySerializer(summary).data)

class ThemeAnalyticsView(APIView):
    """Simple analytics endpoint exposing coverage of a theme across books."""

    def get(self, request, pk):
        theme = Theme.objects.get(pk=pk)
        keywords = [kw.word.lower() for kw in theme.keywords.all()]
        coverage = []
        for book in Book.objects.all():
            text = " ".join(
                v.text for c in book.chapters.all() for v in c.verses.all()
            ).lower()
            freq = TextAnalyticsService.word_frequency(text)
            count = sum(freq.get(k, 0) for k in keywords)
            coverage.append({"book": book.name, "keyword_count": count})
        return Response({"theme": theme.name, "coverage": coverage})
