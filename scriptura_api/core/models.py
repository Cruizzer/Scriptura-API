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

    def __str__(self):
        return f"{self.chapter.book.name} {self.chapter.number}:{self.number}"