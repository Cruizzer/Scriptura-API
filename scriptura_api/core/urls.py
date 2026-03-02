from rest_framework.routers import DefaultRouter
from .views import BookViewSet, ChapterViewSet, VerseViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'chapters', ChapterViewSet)
router.register(r'verses', VerseViewSet)

urlpatterns = router.urls