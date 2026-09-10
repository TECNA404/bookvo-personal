from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Book, Chapter, SavedWord


class BookSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    cover_image = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Book
        fields = [
            "id",
            "owner",
            "title",
            "author",
            "year",
            "genre",
            "cover_url",
            "gutenberg_id",
            "cover_image",
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
            "owner",
            "progress",
            "created_at",
            "updated_at",
        ]

    def validate_progress(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError(
                "Progress must be between 0 and 100."
            )
        return value


class ChapterSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
    )

    class Meta:
        model = Chapter
        fields = [
            "id",
            "book",
            "number",
            "title",
            "content",
            "audio_url",
        ]
        read_only_fields = ["id"]

    def validate_book(self, book):
        request = self.context.get("request")

        if request and book.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You can use chapters only with your own books."
            )

        return book


class SavedWordSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    book = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = SavedWord
        fields = [
            "id",
            "user",
            "word",
            "translation",
            "context",
            "book",
            "is_learned",
            "times_reviewed",
            "next_review_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "times_reviewed",
            "next_review_at",
            "created_at",
        ]

    def validate_book(self, book):
        request = self.context.get("request")

        if book and request and book.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You can use only your own books."
            )

        return book


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
        ]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)