from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, filters, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.types import OpenApiTypes

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
    """Compute analytics for a specific book.
    
    Returns word count and linguistic statistics for the entire book text.
    **No authentication required.**
    """

    @extend_schema(
        description="Get word count and text statistics for a specific book",
        responses={200: OpenApiTypes.OBJECT}
    )
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


@extend_schema_view(
    list=extend_schema(
        description="List all books in the Bible, optionally filtered by testament"
    ),
    retrieve=extend_schema(
        description="Get detailed information about a specific book, including all chapters"
    )
)
class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to books of the Bible.
    
    List and retrieve books with optional filtering by testament and search.
    **No authentication required.**
    """
    queryset = repositories.BookRepository.all()
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['testament']
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookDetailSerializer
        return BookSerializer


@extend_schema_view(
    list=extend_schema(
        description="List chapters, optionally filtered by book name or chapter number"
    ),
    retrieve=extend_schema(
        description="Get a specific chapter with all verses and footnotes"
    )
)
class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to chapters.
    
    List chapters with optional filtering, or retrieve a specific chapter with all verses.
    **No authentication required.**
    """
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


@extend_schema_view(
    list=extend_schema(
        description="Search and filter verses across the entire Bible"
    ),
    retrieve=extend_schema(
        description="Get a specific verse by ID"
    )
)
class VerseViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to Bible verses.
    
    Search and filter verses by book, chapter, or text content. Supports both
    simple field filtering and full-text search.
    **No authentication required.**
    """
    queryset = repositories.VerseRepository.all()
    serializer_class = VerseSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = VerseFilter
    search_fields = ['text']


@extend_schema_view(
    list=extend_schema(
        description="List all collections. Authenticated users see their own private collections; anonymous users see shared collections."
    ),
    create=extend_schema(
        description="Create a new collection. Authenticated users create private collections; anonymous users create shared collections."
    ),
    retrieve=extend_schema(
        description="Get a specific collection with all verses"
    ),
    update=extend_schema(
        description="Update a collection (replace all verses and themes)"
    ),
    partial_update=extend_schema(
        description="Partially update a collection (update specific fields)"
    ),
    destroy=extend_schema(
        description="Delete a collection"
    )
)
class CollectionViewSet(viewsets.ModelViewSet):
    """User-curated collections of verses.
    
    Create collections of verses for later reference. Authenticated users have private collections;
    unauthenticated users can create shared collections that are visible to all.
    **No authentication required, but behavior differs for authenticated vs anonymous users.**
    """
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        """Return all collections. Frontend will filter by user for display."""
        return Collection.objects.all().prefetch_related('verses', 'themes')

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