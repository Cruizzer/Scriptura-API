from rest_framework import viewsets
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from .models import Theme, ThemeKeyword
from .serializers import ThemeSerializer, ThemeKeywordSerializer

@extend_schema_view(
    list=extend_schema(
        summary="List all theme keywords",
        description=(
            "Returns every keyword across all themes.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Themes'],
    ),
    create=extend_schema(
        summary="Add a keyword to a theme",
        description=(
            "Creates a new keyword and associates it with a theme via the `theme` field (theme ID).\n\n"
            "**Authentication:** not required."
        ),
        tags=['Themes'],
    ),
    retrieve=extend_schema(
        summary="Get a single theme keyword",
        description=(
            "Returns a single keyword record identified by its `keyword_id`.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the ThemeKeyword record.')
        ],
        tags=['Themes'],
    ),
    update=extend_schema(
        summary="Replace a theme keyword",
        description="Replaces the keyword word and/or its theme association.\n\n**Authentication:** not required.",
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the ThemeKeyword record.')
        ],
        tags=['Themes'],
    ),
    partial_update=extend_schema(
        summary="Partially update a theme keyword",
        description="Updates only the supplied fields on a keyword.\n\n**Authentication:** not required.",
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the ThemeKeyword record.')
        ],
        tags=['Themes'],
    ),
    destroy=extend_schema(
        summary="Delete a theme keyword",
        description="Permanently removes a keyword from its theme.\n\n**Authentication:** not required.",
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the ThemeKeyword record.')
        ],
        tags=['Themes'],
    ),
)
class ThemeKeywordViewSet(viewsets.ModelViewSet):
    """Manage individual keywords that belong to a theme."""
    queryset = ThemeKeyword.objects.all()
    serializer_class = ThemeKeywordSerializer

@extend_schema_view(
    list=extend_schema(
        summary="List all themes",
        description=(
            "Returns all user-defined themes. Each item includes an `occurrences_endpoint` "
            "URL pointing to `GET /api/analytics/themes/{theme_id}/` for keyword coverage data.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Themes'],
    ),
    create=extend_schema(
        summary="Create a new theme",
        description=(
            "Creates a theme (a named group of keywords). After creation, add keywords via "
            "`POST /api/theme-keywords/` or include them in the request body.\n\n"
            "**Authentication:** not required."
        ),
        tags=['Themes'],
    ),
    retrieve=extend_schema(
        summary="Get a single theme",
        description=(
            "Returns a theme identified by its `theme_id` with all its keywords. "
            "Use the `occurrences_endpoint` in the response to get keyword coverage "
            "across books (`GET /api/analytics/themes/{theme_id}/`).\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the theme.')
        ],
        tags=['Themes'],
    ),
    update=extend_schema(
        summary="Replace a theme",
        description="Replaces all fields on a theme.\n\n**Authentication:** not required.",
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the theme.')
        ],
        tags=['Themes'],
    ),
    partial_update=extend_schema(
        summary="Partially update a theme",
        description="Updates only the supplied fields on a theme.\n\n**Authentication:** not required.",
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the theme.')
        ],
        tags=['Themes'],
    ),
    destroy=extend_schema(
        summary="Delete a theme",
        description=(
            "Permanently deletes a theme and all its keywords.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the theme.')
        ],
        tags=['Themes'],
    ),
)
class ThemeViewSet(viewsets.ModelViewSet):
    """User-defined themes for grouping and analysing biblical concepts."""
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer