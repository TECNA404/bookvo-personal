from rest_framework import serializers

from .models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "year",
            "genre",
            "cover_url",
            "status",
            "progress",
            "pages_total",
            "pages_read",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "progress",
            "created_at",
            "updated_at",
        ]