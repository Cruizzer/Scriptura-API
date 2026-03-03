from django.contrib import admin
from .models import BookSummary


@admin.register(BookSummary)
class BookSummaryAdmin(admin.ModelAdmin):
    list_display = ['book', 'word_count', 'entropy', 'ttr', 'hapax_count', 'updated']
    list_filter = ['book__testament']
    search_fields = ['book__name']
    readonly_fields = ['updated']
