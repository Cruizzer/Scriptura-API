from rest_framework import serializers
from .models import Theme, ThemeKeyword

class ThemeKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeKeyword
        fields = ['id', 'word']

class ThemeSerializer(serializers.ModelSerializer):
    keywords = ThemeKeywordSerializer(many=True, read_only=True)

    class Meta:
        model = Theme
        fields = ['id', 'name', 'keywords']