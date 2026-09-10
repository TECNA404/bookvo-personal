from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Book
from .serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author", "genre"]
    ordering_fields = ["created_at", "updated_at", "progress", "year"]

    def get_queryset(self):
        queryset = Book.objects.filter(owner=self.request.user)

        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        books = self.get_queryset()

        total = books.count()
        planning = books.filter(status="planning").count()
        reading = books.filter(status="reading").count()
        finished = books.filter(status="finished").count()

        if total:
            average_progress = round(
                sum(book.progress for book in books) / total
            )
        else:
            average_progress = 0

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
                {"detail": "Передайте ціле число у полі pages_read."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pages_read < 0:
            return Response(
                {"detail": "pages_read не може бути від’ємним."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if book.pages_total and pages_read > book.pages_total:
            return Response(
                {"detail": "Прочитаних сторінок не може бути більше за загальну кількість."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book.pages_read = pages_read
        book.save()

        return Response(BookSerializer(book).data)

    @action(detail=True, methods=["patch"], url_path="finish")
    def finish_book(self, request, pk=None):
        book = self.get_object()

        book.status = "finished"

        if book.pages_total:
            book.pages_read = book.pages_total
            book.progress = 100

        book.save()

        return Response(BookSerializer(book).data)