from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, filters

from django_filters import rest_framework as django_filters

from .models import Book, Chapter, Verse
from .serializers import (
    BookSerializer,
    BookDetailSerializer,
    ChapterListSerializer,
    ChapterSerializer,
    VerseSerializer
)
from . import repositories
from analytics.services.text_analytics import TextAnalyticsService


class BookAnalyticsView(APIView):
    """An example endpoint that delegates to the service layer.

    In production projects the analytics app would expose its own
    viewset and serializers; this stub simply demonstrates separation of
    concerns and use of the repository.
    """

    def get(self, request, pk):
        book = repositories.BookRepository.get(pk)
        # build the full text string once and hand off to service
        full_text = " ".join(
            v.text for c in book.chapters.all() for v in c.verses.all()
        )
        return Response({
            "book": book.name,
            "word_count": TextAnalyticsService.word_count(full_text)
        })


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = repositories.BookRepository.all()
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['testament']
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookDetailSerializer
        return BookSerializer


class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = repositories.ChapterRepository.all()
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ['book__name', 'number']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChapterSerializer  # full verses only for detail view
        return ChapterListSerializer  # lightweight for list




# improved filtering and search options for verses
class VerseFilter(django_filters.FilterSet):
    book = django_filters.CharFilter(field_name='chapter__book__name', lookup_expr='iexact')
    chapter = django_filters.NumberFilter(field_name='chapter__number')
    contains = django_filters.CharFilter(field_name='text', lookup_expr='icontains')

    class Meta:
        model = Verse
        fields = ['book', 'chapter', 'contains']


class VerseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = repositories.VerseRepository.all()
    serializer_class = VerseSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = VerseFilter
    search_fields = ['text']