from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from .models import Theme, ThemeKeyword

class ThemeKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeKeyword
        fields = ['id', 'theme', 'word']

class ThemeSerializer(serializers.ModelSerializer):
    keywords = ThemeKeywordSerializer(many=True, read_only=True)
    occurrences_endpoint = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Theme
        fields = ['id', 'name', 'keywords', 'occurrences_endpoint']

    @extend_schema_field(OpenApiTypes.STR)
    def get_occurrences_endpoint(self, obj) -> str:
        return f"/api/analytics/themes/{obj.id}/"
    
    def create(self, validated_data):
        keywords_data = self.initial_data.get('keywords', [])
        theme = Theme.objects.create(**validated_data)
        
        for keyword in keywords_data:
            if isinstance(keyword, dict):
                ThemeKeyword.objects.create(theme=theme, word=keyword.get('word', ''))
            elif isinstance(keyword, str):
                ThemeKeyword.objects.create(theme=theme, word=keyword)
        
        return theme