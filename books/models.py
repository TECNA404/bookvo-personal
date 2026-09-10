from django.contrib.auth.models import User
from django.db import models


class Book(models.Model):
    STATUS_CHOICES = [
        ("planning", "Планую"),
        ("reading", "Читаю"),
        ("finished", "Прочитав"),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="books",
    )
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    year = models.IntegerField(null=True, blank=True)
    genre = models.CharField(max_length=100, blank=True)
    cover_url = models.URLField(blank=True)
    gutenberg_id = models.PositiveIntegerField(null=True, blank=True)
    cover_image = models.ImageField(
        upload_to="covers/",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="planning",
    )
    progress = models.PositiveSmallIntegerField(default=0)
    pages_total = models.PositiveIntegerField(null=True, blank=True)
    pages_read = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "gutenberg_id"],
                name="unique_gutenberg_book_per_owner",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pages_total and self.pages_read is not None:
            self.pages_read = min(self.pages_read, self.pages_total)
            self.progress = int(self.pages_read / self.pages_total * 100)

        if self.progress == 100:
            self.status = "finished"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} — {self.author or 'без автора'}"


class Chapter(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="chapters",
    )
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    audio_url = models.URLField(blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "number"],
                name="unique_chapter_number_per_book",
            )
        ]

    def __str__(self):
        return f"{self.book.title} — Chapter {self.number}"


class SavedWord(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_words",
    )
    word = models.CharField(max_length=120)
    translation = models.CharField(max_length=255)
    context = models.TextField(blank=True)
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saved_words",
    )
    is_learned = models.BooleanField(default=False)
    times_reviewed = models.PositiveIntegerField(default=0)
    next_review_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_learned", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "word"],
                name="unique_saved_word_per_user",
            )
        ]

    def __str__(self):
        return f"{self.word} — {self.translation}"