from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import BookViewSet, ChapterViewSet, VerseViewSet, BookAnalyticsView
from themes.views import ThemeViewSet, ThemeKeywordViewSet
from analytics.views import BookSummaryViewSet, ThemeAnalyticsView

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'chapters', ChapterViewSet)
router.register(r'verses', VerseViewSet)
router.register(r'themes', ThemeViewSet)
router.register(r'theme-keywords', ThemeKeywordViewSet)
router.register(r'book-summaries', BookSummaryViewSet, basename='booksummary')

urlpatterns = router.urls

# extra custom analytics endpoints
urlpatterns += [
    path('themes/<int:pk>/coverage/', ThemeAnalyticsView.as_view(), name='theme-coverage'),
]