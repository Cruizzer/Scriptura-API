from django.shortcuts import render
from rest_framework import viewsets
from .models import Theme
from .serializers import ThemeSerializer

class ThemeViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD for Themes.
    """
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer