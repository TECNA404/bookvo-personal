from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    STATUS_CHOICES = [
        ("planning", "Планую"),
        ("reading", "Читаю"),
        ("finished", "Прочитав"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="books")
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    year = models.IntegerField(null=True, blank=True)
    genre = models.CharField(max_length=100, blank=True)
    cover_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning")
    progress = models.PositiveSmallIntegerField(default=0)  # 0–100
    pages_total = models.PositiveIntegerField(null=True, blank=True)
    pages_read = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        if self.pages_total is not None and self.pages_total > 0:
            self.pages_read = min(self.pages_read or 0, self.pages_total)
            self.progress = int(self.pages_read / self.pages_total * 100)

        if self.progress == 100:
            self.status = "finished"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} — {self.author or 'без автора'}"