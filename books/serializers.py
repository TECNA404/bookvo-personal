from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            "id", "title", "author", "year", "genre", "cover_url",
            "status", "progress", "pages_total", "pages_read", "notes",
            "created_at", "updated_at"
        ]
        read_only_fields = ["owner", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        return Book.objects.create(owner=request.user, **validated_data)