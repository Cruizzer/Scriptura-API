from django.contrib import admin
from .models import Theme, ThemeKeyword


class ThemeKeywordInline(admin.TabularInline):
    model = ThemeKeyword
    extra = 3


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'keyword_count']
    search_fields = ['name']
    inlines = [ThemeKeywordInline]

    def keyword_count(self, obj):
        return obj.keywords.count()
    keyword_count.short_description = 'Keywords'


@admin.register(ThemeKeyword)
class ThemeKeywordAdmin(admin.ModelAdmin):
    list_display = ['word', 'theme']
    list_filter = ['theme']
    search_fields = ['word', 'theme__name']
