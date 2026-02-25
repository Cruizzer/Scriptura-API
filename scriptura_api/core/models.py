from django.db import models


class Book(models.Model):
    name = models.CharField(max_length=100)
    testament = models.CharField(max_length=20)  # Old / New Testament
    order = models.IntegerField()

    def __str__(self):
        return self.name

class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    number = models.IntegerField()

    def __str__(self):
        return f"{self.book.name} {self.number}"

class Verse(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="verses")
    number = models.IntegerField()
    text = models.TextField()

    def __str__(self):
        return f"{self.chapter.book.name} {self.chapter.number}:{self.number}"