from rest_framework import viewsets
from drf_spectacular.utils import extend_schema_view, extend_schema
from .models import Theme, ThemeKeyword
from .serializers import ThemeSerializer, ThemeKeywordSerializer

@extend_schema_view(
    list=extend_schema(
        description="List all themes (tags for grouping biblical concepts)"
    ),
    create=extend_schema(
        description="Create a new theme with initial keywords"
    ),
    retrieve=extend_schema(
        description="Get a specific theme with all its keywords"
    ),
    update=extend_schema(
        description="Update a theme"
    ),
    destroy=extend_schema(
        description="Delete a theme"
    )
)
class ThemeKeywordViewSet(viewsets.ModelViewSet):
    """Manage keywords within themes.
    
    Add, update, or remove individual keywords from themes.
    **No authentication required.**
    """
    queryset = ThemeKeyword.objects.all()
    serializer_class = ThemeKeywordSerializer

@extend_schema_view(
    list=extend_schema(
        description="List all user-defined themes for organizing biblical concepts. Each item includes `occurrences_endpoint` to query analytics occurrences for that theme."
    ),
    create=extend_schema(
        description="Create a new custom theme with keywords. Response includes `occurrences_endpoint` for analytics occurrences by theme ID."
    ),
    retrieve=extend_schema(
        description="Get a specific theme with all its keywords and `occurrences_endpoint` for analytics lookup."
    ),
    update=extend_schema(
        description="Update a theme and its keywords"
    ),
    destroy=extend_schema(
        description="Delete a theme and all its keywords"
    )
)
class ThemeViewSet(viewsets.ModelViewSet):
    """User-defined themes and biblical concepts.
    
    Create custom themes (tags) to organize and group biblical concepts.
    Each theme can have multiple keywords for searching.
    **No authentication required.**
    """
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer