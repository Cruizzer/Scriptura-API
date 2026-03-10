from rest_framework import viewsets
from .models import Theme, ThemeKeyword
from .serializers import ThemeSerializer, ThemeKeywordSerializer

class ThemeKeywordViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD for Theme Keywords.
    """
    queryset = ThemeKeyword.objects.all()
    serializer_class = ThemeKeywordSerializer

class ThemeViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD for Themes.
    """
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer