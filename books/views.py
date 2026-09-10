from datetime import timedelta

import requests

from django.utils import timezone

from rest_framework import (
    filters,
    generics,
    permissions,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_serializers import RegisterSerializer
from .epub_importer import import_epub
from .gutendex import get_catalog_books, import_gutenberg_book
from .models import Book, Chapter, SavedWord
from .serializers import (
    BookSerializer,
    ChapterSerializer,
    SavedWordSerializer,
)

class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author", "genre"]
    ordering_fields = ["created_at", "updated_at", "progress", "year", "title"]

    def get_queryset(self):
        queryset = Book.objects.filter(owner=self.request.user)

        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(
        detail=False,
        methods=["get"],
        url_path="catalog/search",
    )
    def catalog_search(self, request):
        query = request.query_params.get("q", "").strip()
        page = request.query_params.get("page", 1)

        try:
            page = int(page)
        except ValueError:
            page = 1

        try:
            result = get_catalog_books(query=query, page=page)
        except Exception as error:
            return Response(
                {
                    "detail": "Не удалось получить книги из внешнего каталога.",
                    "error": str(error),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result)

    @action(
        detail=False,
        methods=["post"],
        url_path=r"catalog/import/(?P<gutenberg_id>[^/.]+)",
    )
    def catalog_import(self, request, gutenberg_id=None):
        try:
            gutenberg_id = int(gutenberg_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "gutenberg_id должен быть числом."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            book = import_gutenberg_book(
                request.user,
                gutenberg_id,
            )
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"detail": "Не удалось импортировать книгу."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            BookSerializer(
                book,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="import-epub",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_epub_file(self, request):
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {"detail": "Передайте EPUB-файл в поле file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not uploaded_file.name.lower().endswith(".epub"):
            return Response(
                {"detail": "Поддерживаются только файлы .epub."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book = import_epub(request.user, uploaded_file)

        return Response(
            BookSerializer(book, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        books = self.get_queryset()

        total = books.count()
        planning = books.filter(status="planning").count()
        reading = books.filter(status="reading").count()
        finished = books.filter(status="finished").count()

        average_progress = 0
        if total:
            average_progress = round(
                sum(book.progress for book in books) / total
            )

        return Response({
            "total": total,
            "planning": planning,
            "reading": reading,
            "finished": finished,
            "average_progress": average_progress,
        })

    @action(detail=True, methods=["patch"], url_path="progress")
    def update_progress(self, request, pk=None):
        book = self.get_object()

        try:
            pages_read = int(request.data["pages_read"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {"detail": "Передайте целое число в поле pages_read."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pages_read < 0:
            return Response(
                {"detail": "pages_read не может быть отрицательным."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if book.pages_total and pages_read > book.pages_total:
            return Response(
                {"detail": "Прочитанных страниц не может быть больше общего числа."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book.pages_read = pages_read
        book.save()

        return Response(
            BookSerializer(book, context={"request": request}).data
        )

    @action(detail=True, methods=["patch"], url_path="finish")
    def finish_book(self, request, pk=None):
        book = self.get_object()

        book.status = "finished"
        book.progress = 100

        if book.pages_total:
            book.pages_read = book.pages_total

        book.save()

        return Response(
            BookSerializer(book, context={"request": request}).data
        )


class ChapterViewSet(viewsets.ModelViewSet):
    serializer_class = ChapterSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["number"]

    def get_queryset(self):
        queryset = Chapter.objects.filter(book__owner=self.request.user)

        book_id = self.request.query_params.get("book")
        if book_id:
            queryset = queryset.filter(book_id=book_id)

        return queryset

    def perform_create(self, serializer):
        book = serializer.validated_data["book"]

        if book.owner_id != self.request.user.id:
            raise permissions.PermissionDenied(
                "Нельзя добавлять главы к чужой книге."
            )

        serializer.save()


class SavedWordViewSet(viewsets.ModelViewSet):
    serializer_class = SavedWordSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["word", "translation", "context"]
    ordering_fields = ["created_at", "word", "times_reviewed"]

    def get_queryset(self):
        queryset = SavedWord.objects.filter(user=self.request.user)

        learned_value = self.request.query_params.get("learned")
        if learned_value in ("true", "false"):
            queryset = queryset.filter(
                is_learned=(learned_value == "true")
            )

        book_id = self.request.query_params.get("book")
        if book_id:
            queryset = queryset.filter(book_id=book_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["patch"], url_path="review")
    def review_word(self, request, pk=None):
        word = self.get_object()
        result = request.data.get("result")

        if result not in ("known", "again"):
            return Response(
                {"detail": "Передайте result: 'known' или 'again'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        word.times_reviewed += 1

        if result == "known":
            word.is_learned = True
            word.next_review_at = timezone.now() + timedelta(days=3)
        else:
            word.is_learned = False
            word.next_review_at = timezone.now() + timedelta(minutes=10)

        word.save()

        return Response(SavedWordSerializer(word).data)

    @action(detail=False, methods=["get"], url_path="due")
    def due_words(self, request):
        now = timezone.now()

        queryset = self.get_queryset().filter(is_learned=False)
        words = queryset.filter(next_review_at__isnull=True) | queryset.filter(
            next_review_at__lte=now
        )

        words = words.order_by("next_review_at", "created_at")

        return Response(SavedWordSerializer(words, many=True).data)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class TranslateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        text = request.query_params.get("text", "").strip()
        target = request.query_params.get("target", "ru").strip()

        if not text:
            return Response(
                {"detail": "Параметр text обязателен."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(text) > 500:
            return Response(
                {"detail": "Текст не должен быть длиннее 500 символов."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text,
                "langpair": f"en|{target}",
            },
            timeout=15,
        )

        if not response.ok:
            return Response(
                {"detail": "Сервис перевода временно недоступен."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        data = response.json()
        response_data = data.get("responseData") or {}

        return Response(
            {
                "text": text,
                "target": target,
                "translation": response_data.get(
                    "translatedText",
                    "",
                ),
            }
        )