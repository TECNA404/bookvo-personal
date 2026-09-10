from django.contrib import admin
from .models import Book

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "status", "progress", "owner", "updated_at"]
    list_filter = ["status", "owner"]
    search_fields = ["title", "author"]