from django.contrib import admin

from .models import Book, Chapter, SavedWord


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "author",
        "status",
        "progress",
        "owner",
        "updated_at",
    ]
    list_filter = ["status", "owner"]
    search_fields = ["title", "author"]
    inlines = [ChapterInline]


@admin.register(SavedWord)
class SavedWordAdmin(admin.ModelAdmin):
    list_display = [
        "word",
        "translation",
        "user",
        "book",
        "is_learned",
        "times_reviewed",
        "created_at",
    ]
    list_filter = ["is_learned", "user"]
    search_fields = ["word", "translation"]