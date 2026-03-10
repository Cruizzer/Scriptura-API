from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, filters, permissions

from django_filters import rest_framework as django_filters

from .models import Verse, Collection
from .serializers import (
    BookSerializer,
    BookDetailSerializer,
    ChapterListSerializer,
    ChapterSerializer,
    VerseSerializer,
    CollectionSerializer,
    CollectionWriteSerializer
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

    def get_queryset(self):
        qs = repositories.ChapterRepository.all()
        if self.action == 'retrieve':
            return qs.prefetch_related('sections', 'verses__footnotes')
        return qs

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


class CollectionViewSet(viewsets.ModelViewSet):
    """
    Provides full CRUD for user-curated verse collections.
    
    Endpoints:
    - GET /api/collections/ - List all collections for authenticated user
    - POST /api/collections/ - Create a new collection
    - GET /api/collections/{id}/ - Get a specific collection
    - PUT /api/collections/{id}/ - Update a collection
    - DELETE /api/collections/{id}/ - Delete a collection
    """
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        """Filter collections by authenticated user, or return anonymous collections"""
        if self.request.user.is_authenticated:
            return Collection.objects.filter(user=self.request.user).prefetch_related('verses', 'themes')
        # Return anonymous (user=None) collections for unauthenticated users
        return Collection.objects.filter(user__isnull=True).prefetch_related('verses', 'themes')

    def perform_create(self, serializer):
        """Automatically set the user to the current authenticated user if available"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectionWriteSerializer
        return CollectionSerializer