from django.db import models

class Theme(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class ThemeKeyword(models.Model):
    theme = models.ForeignKey(
        Theme, 
        related_name="keywords", 
        on_delete=models.CASCADE
    )
    word = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.word} ({self.theme.name})"