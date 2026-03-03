from rest_framework import serializers
from .models import Theme, ThemeKeyword

class ThemeKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeKeyword
        fields = ['id', 'theme', 'word']

class ThemeSerializer(serializers.ModelSerializer):
    keywords = ThemeKeywordSerializer(many=True, read_only=True)

    class Meta:
        model = Theme
        fields = ['id', 'name', 'keywords']
    
    def create(self, validated_data):
        keywords_data = self.initial_data.get('keywords', [])
        theme = Theme.objects.create(**validated_data)
        
        for keyword in keywords_data:
            if isinstance(keyword, dict):
                ThemeKeyword.objects.create(theme=theme, word=keyword.get('word', ''))
            elif isinstance(keyword, str):
                ThemeKeyword.objects.create(theme=theme, word=keyword)
        
        return theme