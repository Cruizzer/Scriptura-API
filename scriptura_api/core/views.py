from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, filters, status, permissions
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers as drf_serializers

from django_filters import rest_framework as django_filters
from django.db.models import Q, Prefetch
from django.contrib.auth.models import User
from django.conf import settings
from google.auth.transport import requests
from google.oauth2 import id_token
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Verse, Collection, Section
from .permissions import IsCollectionOwnerOrReadOnly
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
    """Word count and linguistic statistics for a single book."""

    @extend_schema(
        summary="Book text statistics",
        description=(
            "Returns word count and basic linguistic statistics computed over the "
            "entire text of the requested book.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter(
                name='pk',
                type=int,
                location=OpenApiParameter.PATH,
                description='Primary key of the book (from `GET /api/books/`).',
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=['Analytics'],
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


class GoogleAuthTokenView(APIView):
    """Sign in with Google and receive JWT access + refresh tokens."""
    # Bypass SessionAuthentication (and its CSRF enforcement) for this login endpoint.
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Google sign-in → JWT tokens",
        description=(
            "Verify a **Google `id_token`** (obtained from Google Identity Services in the "
            "browser) and return a pair of JWT tokens for this API.\n\n"
            "**Request body:** `{ \"token\": \"<google_id_token>\" }`\n\n"
            "**Response:** `access` token (valid 1 h), `refresh` token (valid 7 d), "
            "plus basic user info and Google profile picture URL.\n\n"
            "**Authentication:** not required."
        ),
        request=inline_serializer(
            name='GoogleTokenRequest',
            fields={'token': drf_serializers.CharField(help_text='Google id_token from the GIS browser flow.')},
        ),
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access':   {'type': 'string', 'description': 'JWT access token (1 hour lifetime).'},
                    'refresh':  {'type': 'string', 'description': 'JWT refresh token (7 day lifetime).'},
                    'user_id':  {'type': 'integer'},
                    'email':    {'type': 'string'},
                    'username': {'type': 'string'},
                    'picture':  {'type': 'string', 'description': 'Google profile picture URL.'},
                }
            },
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        auth=[],
        tags=['Authentication'],
    )
    def post(self, request):
        google_token = request.data.get('token')

        if not google_token:
            return Response({'error': 'token field is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not settings.GOOGLE_CLIENT_ID:
            return Response({'error': 'GOOGLE_CLIENT_ID is not configured on the server'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # Verify the Google token
            idinfo = id_token.verify_oauth2_token(
                google_token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = idinfo.get('email')
            if not email:
                return Response({'error': 'Email not found in token'}, status=status.HTTP_400_BAD_REQUEST)

            local_part = email.split('@')[0]
            existing = User.objects.filter(email=email).first()

            # Get or create user
            if existing:
                user = existing
            else:
                username = local_part
                suffix = 1
                while User.objects.filter(username=username).exists():
                    username = f"{local_part}{suffix}"
                    suffix += 1
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=idinfo.get('given_name', ''),
                    last_name=idinfo.get('family_name', ''),
                )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_id': user.id,
                'email': user.email,
                'username': user.username,
                'picture': idinfo.get('picture', ''),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class AuthMeView(APIView):
    """Return the profile of the currently authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Current user profile",
        description=(
            "Returns the profile of the user identified by the JWT Bearer token in the "
            "`Authorization` header.\n\n"
            "**Authentication:** required (Bearer token)."
        ),
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'id':         {'type': 'integer'},
                    'username':   {'type': 'string'},
                    'email':      {'type': 'string'},
                    'first_name': {'type': 'string'},
                    'last_name':  {'type': 'string'},
                }
            },
            401: OpenApiTypes.OBJECT,
        },
        tags=['Authentication'],
    )
    def get(self, request):
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })


class LogoutView(APIView):
    """Invalidate a refresh token (JWT logout)."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Logout (blacklist refresh token)",
        description=(
            "Adds the provided refresh token to the blacklist so it can no longer be "
            "used to obtain new access tokens.\n\n"
            "**Request body:** `{ \"refresh\": \"<refresh_token>\" }`\n\n"
            "**Authentication:** required (Bearer token)."
        ),
        request=inline_serializer(
            name='LogoutRequest',
            fields={'refresh': drf_serializers.CharField(help_text='The JWT refresh token to invalidate.')},
        ),
        responses={
            200: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        tags=['Authentication'],
    )
    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response({'error': 'refresh field is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh)
            token.blacklist()
            return Response({'detail': 'Logged out successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="List all books",
        description=(
            "Returns all books of the Bible. Filter by `testament` (`OT` or `NT`) "
            "or search by name.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Bible'],
    ),
    retrieve=extend_schema(
        summary="Get a single book",
        description=(
            "Returns full details for a book identified by its `book_id`, including "
            "a list of all chapters.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the book (from `GET /api/books/`).')
        ],
        tags=['Bible'],
    ),
)
class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to books of the Bible."""
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
        summary="List chapters",
        description=(
            "Returns chapters, optionally filtered by `book__name` (exact match) "
            "or `number` (chapter number).\n\n"
            "**Authentication:** not required."
        ),
        tags=['Bible'],
    ),
    retrieve=extend_schema(
        summary="Get a single chapter",
        description=(
            "Returns a chapter identified by its `chapter_id` with all its verses "
            "(including text and footnotes) and section headings.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the chapter (from `GET /api/chapters/`).')
        ],
        tags=['Bible'],
    ),
)
class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to Bible chapters with verses and footnotes."""
    queryset = repositories.ChapterRepository.all()
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ['book__name', 'number']

    def get_queryset(self):
        qs = repositories.ChapterRepository.all()
        if self.action == 'retrieve':
            return qs.prefetch_related(
                Prefetch('sections', queryset=Section.objects.order_by('start_verse', 'id')),
                Prefetch(
                    'verses',
                    queryset=Verse.objects.order_by('number').prefetch_related('footnotes')
                ),
            )
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
        summary="Search and filter verses",
        description=(
            "Returns Bible verses. Supports three filter parameters:\n\n"
            "- `book` — book name, case-insensitive (e.g. `Genesis`)\n"
            "- `chapter` — chapter number (integer)\n"
            "- `contains` — substring search within verse text\n\n"
            "Also supports full-text `search` via the `search` query parameter.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Bible'],
    ),
    retrieve=extend_schema(
        summary="Get a single verse",
        description=(
            "Returns a single verse identified by its `verse_id`.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the verse (from `GET /api/verses/`).')
        ],
        tags=['Bible'],
    ),
)
class VerseViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to individual Bible verses."""
    queryset = repositories.VerseRepository.all()
    serializer_class = VerseSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = VerseFilter
    search_fields = ['text']

    def get_queryset(self):
        if self.action == 'retrieve':
            return repositories.VerseRepository.with_details()
        return repositories.VerseRepository.all()


@extend_schema_view(
    list=extend_schema(
        summary="List visible collections",
        description=(
            "Returns verse collections visible to the caller:\n\n"
            "- **Unauthenticated:** only collections marked `is_public = true`.\n"
            "- **Authenticated:** all public collections **plus** the caller's own private ones.\n\n"
            "Supports `search` query parameter (matches `name` and `description`).\n\n"
            "**Authentication:** optional."
        ),
        tags=['Collections'],
    ),
    create=extend_schema(
        summary="Create a new collection",
        description=(
            "Creates a new collection owned by the authenticated user. "
            "Set `is_public: true` to make it visible to everyone "
            "(your username will be shown as creator).\n\n"
            "**Authentication:** required (Bearer token)."
        ),
        tags=['Collections'],
    ),
    retrieve=extend_schema(
        summary="Get a collection with its verses",
        description=(
            "Returns a collection identified by its `collection_id` together with "
            "all its verses (full text, book, chapter, and verse number).\n\n"
            "- Public collections are readable by anyone.\n"
            "- Private collections are readable only by their owner.\n\n"
            "**Authentication:** optional (required for private collections)."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the collection.')
        ],
        tags=['Collections'],
    ),
    update=extend_schema(
        summary="Replace a collection (full update)",
        description=(
            "Replaces all writable fields on the collection. "
            "You must supply `name`, `description`, `is_public`, and `verses` (list of verse IDs).\n\n"
            "**Authentication:** required — only the owner can update a collection."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the collection.')
        ],
        tags=['Collections'],
    ),
    partial_update=extend_schema(
        summary="Update a collection (partial)",
        description=(
            "Updates only the supplied fields on the collection. "
            "Commonly used to rename, toggle `is_public`, or change the verse list.\n\n"
            "**Authentication:** required — only the owner can update a collection."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the collection.')
        ],
        tags=['Collections'],
    ),
    destroy=extend_schema(
        summary="Delete a collection",
        description=(
            "Permanently deletes a collection.\n\n"
            "**Authentication:** required — only the owner can delete a collection."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the collection.')
        ],
        tags=['Collections'],
    ),
)
class CollectionViewSet(viewsets.ModelViewSet):
    """User-curated collections of Bible verses."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCollectionOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        """Return collections visible to the current user.
        
        Authenticated users see all public collections plus their own private ones.
        Unauthenticated users see only public collections.
        """
        if self.request.user.is_authenticated:
            return Collection.objects.filter(
                Q(is_public=True) | Q(user=self.request.user)
            ).prefetch_related('verses')
        return Collection.objects.filter(is_public=True).prefetch_related('verses')

    def perform_create(self, serializer):
        """Always set owner to current authenticated user."""
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectionWriteSerializer
        return CollectionSerializer