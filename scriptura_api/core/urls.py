from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import BookViewSet, ChapterViewSet, VerseViewSet, BookAnalyticsView, CollectionViewSet
from themes.views import ThemeViewSet, ThemeKeywordViewSet
from analytics.views import (
    BookSummaryViewSet,
    ThemeAnalyticsView,
    LexicalSimilarityGraphView,
    VerseRecommendationView
)

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'chapters', ChapterViewSet)
router.register(r'verses', VerseViewSet)
router.register(r'themes', ThemeViewSet)
router.register(r'theme-keywords', ThemeKeywordViewSet)
router.register(r'book-summaries', BookSummaryViewSet, basename='booksummary')
router.register(r'collections', CollectionViewSet, basename='collection')

urlpatterns = router.urls

# extra custom analytics endpoints
urlpatterns += [
    path('themes/<int:pk>/coverage/', ThemeAnalyticsView.as_view(), name='theme-coverage'),
    path('analytics/similarity-graph/', LexicalSimilarityGraphView.as_view(), name='similarity-graph'),
    path('analytics/verse-recommendations/', VerseRecommendationView.as_view(), name='verse-recommendations'),
]