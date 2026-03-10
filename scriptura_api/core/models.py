from django.db import models


class Book(models.Model):
    name = models.CharField(max_length=100)
    testament = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Chapter(models.Model):
    book = models.ForeignKey(
        Book,
        related_name='chapters',
        on_delete=models.CASCADE
    )
    number = models.IntegerField()

    def __str__(self):
        return f"{self.book.name} {self.number}"


class Verse(models.Model):
    chapter = models.ForeignKey(
        Chapter,
        related_name='verses',
        on_delete=models.CASCADE
    )
    number = models.IntegerField()
    text = models.TextField()
    paragraph_start = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.chapter.book.name} {self.chapter.number}:{self.number}"


class Section(models.Model):
    chapter = models.ForeignKey(
        Chapter,
        related_name='sections',
        on_delete=models.CASCADE
    )
    start_verse = models.IntegerField()
    title = models.CharField(max_length=255)

    class Meta:
        ordering = ['start_verse', 'id']

    def __str__(self):
        return f"{self.chapter.book.name} {self.chapter.number}:{self.start_verse} - {self.title}"


class Footnote(models.Model):
    verse = models.ForeignKey(
        Verse,
        related_name='footnotes',
        on_delete=models.CASCADE
    )
    marker = models.CharField(max_length=20, blank=True, default='')
    text = models.TextField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        marker = self.marker if self.marker else '*'
        return f"{self.verse} [{marker}]"


class Collection(models.Model):
    """User-curated collection of verses and themes."""
    user = models.ForeignKey(
        'auth.User',
        related_name='collections',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    verses = models.ManyToManyField(
        Verse,
        related_name='collections',
        blank=True
    )
    themes = models.ManyToManyField(
        'themes.Theme',
        related_name='collections',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name