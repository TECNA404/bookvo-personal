from rest_framework import serializers

from .models import Book, Chapter, SavedWord


class ChapterSerializer(serializers.ModelSerializer):
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
        read_only_fields = [
            "id",
            "book",
        ]


class BookSerializer(serializers.ModelSerializer):
    chapters_count = serializers.IntegerField(
        source="chapters.count",
        read_only=True,
    )
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "year",
            "genre",
            "cover_url",
            "gutenberg_id",
            "cover_image",
            "cover_image_url",
            "status",
            "progress",
            "pages_total",
            "pages_read",
            "notes",
            "chapters_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "gutenberg_id",
            "progress",
            "chapters_count",
            "created_at",
            "updated_at",
        ]

    def get_cover_image_url(self, obj):
        request = self.context.get("request")

        if not obj.cover_image:
            return None

        if request:
            return request.build_absolute_uri(obj.cover_image.url)

        return obj.cover_image.url

    def validate_progress(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError(
                "Прогресс должен быть от 0 до 100."
            )

        return value


class SavedWordSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(
        source="book.title",
        read_only=True,
    )

    class Meta:
        model = SavedWord
        fields = [
            "id",
            "word",
            "translation",
            "context",
            "book",
            "book_title",
            "is_learned",
            "times_reviewed",
            "next_review_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "book_title",
            "times_reviewed",
            "next_review_at",
            "created_at",
        ]

    def validate_word(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Слово не может быть пустым."
            )

        return value

    def validate_book(self, book):
        request = self.context["request"]

        if book.owner_id != request.user.id:
            raise serializers.ValidationError(
                "Можно привязать слово только к своей книге."
            )

        return book