from rest_framework.routers import DefaultRouter
from django.urls import path
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .views import (
    BookViewSet,
    ChapterViewSet,
    VerseViewSet,
    BookAnalyticsView,
    CollectionViewSet,
    GoogleAuthTokenView,
    AuthMeView,
    LogoutView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from themes.views import ThemeViewSet, ThemeKeywordViewSet
from analytics.views import (
    BookSummaryViewSet,
    ThemeAnalyticsView,
    LexicalSimilarityGraphView,
    VerseRecommendationView,
    CollectionRecommendationsView
)


# ---------------------------------------------------------------------------
# drf-spectacular requires decorating the *class* method, not as_view().
# These thin subclasses add schema metadata to the simplejwt token endpoints.
# ---------------------------------------------------------------------------

class TokenObtainView(TokenObtainPairView):
    """Obtain a JWT access + refresh token pair via username and password."""

    @extend_schema(
        summary="Obtain JWT token pair (username + password)",
        description=(
            "Exchange a Django **username** and **password** for a JWT `access` token "
            "(valid 1 hour) and a `refresh` token (valid 7 days).\n\n"
            "For Google-authenticated users, use `POST /api/auth/google-token/` instead.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Authentication'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenRefreshSchemaView(TokenRefreshView):
    """Exchange a refresh token for a new access token."""

    @extend_schema(
        summary="Refresh an access token",
        description=(
            "Exchange a valid `refresh` token for a new `access` token.\n\n"
            "**Request body:** `{ \"refresh\": \"<refresh_token>\" }`\n\n"
            "With `ROTATE_REFRESH_TOKENS` enabled, a fresh `refresh` token is also "
            "returned and the old one is blacklisted immediately.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Authentication'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenVerifySchemaView(TokenVerifyView):
    """Verify that a JWT access token is still valid."""

    @extend_schema(
        summary="Verify an access token",
        description=(
            "Check whether a JWT token is still valid and not blacklisted.\n\n"
            "**Request body:** `{ \"token\": \"<access_token>\" }`\n\n"
            "Returns `{}` (HTTP 200) if valid, or HTTP 401 if expired or invalid.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Authentication'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'chapters', ChapterViewSet)
router.register(r'verses', VerseViewSet)
router.register(r'themes', ThemeViewSet)
router.register(r'theme-keywords', ThemeKeywordViewSet)
router.register(r'book-summaries', BookSummaryViewSet, basename='booksummary')
router.register(r'collections', CollectionViewSet, basename='collection')

urlpatterns = router.urls

urlpatterns += [
    path('auth/google-token/', GoogleAuthTokenView.as_view(), name='google-auth-token'),
    path('auth/token/', TokenObtainView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', TokenRefreshSchemaView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifySchemaView.as_view(), name='token-verify'),
    path('auth/me/', AuthMeView.as_view(), name='auth-me'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('analytics/themes/<int:pk>/', ThemeAnalyticsView.as_view(), name='theme-analytics'),
    path('analytics/similarity-graph/', LexicalSimilarityGraphView.as_view(), name='similarity-graph'),
    path('analytics/verse-recommendations/', VerseRecommendationView.as_view(), name='verse-recommendations'),
    path('analytics/collection-recommendations/', CollectionRecommendationsView.as_view(), name='collection-recommendations'),
]