from django.db import models

# Precomputed analytics for a Book.  Metrics are updated by management commands
# or by signals after ingestion so that expensive text processing does not run
# on every API request.


class BookSummary(models.Model):
    book = models.OneToOneField(
        'core.Book',
        related_name='summary',
        on_delete=models.CASCADE
    )
    word_count = models.PositiveIntegerField(default=0)
    entropy = models.FloatField(null=True, blank=True)
    ttr = models.FloatField(null=True, blank=True)
    hapax_count = models.PositiveIntegerField(null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary for {self.book.name}"

# Create your models here.
