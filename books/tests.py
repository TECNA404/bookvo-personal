from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Book, Chapter, SavedWord


class BookApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            password="StrongPassword123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="StrongPassword123",
        )

        self.client.force_authenticate(user=self.user)

        self.book = Book.objects.create(
            owner=self.user,
            title="Alice's Adventures in Wonderland",
            author="Carroll, Lewis",
            pages_total=100,
            pages_read=0,
        )

        self.chapter = Chapter.objects.create(
            book=self.book,
            number=1,
            title="Chapter I",
            content="Alice was beginning to get very tired.",
        )

    def get_results(self, response):
        if isinstance(response.data, dict):
            return response.data.get("results", [])
        return response.data

    def test_user_sees_only_own_books(self):
        Book.objects.create(
            owner=self.other_user,
            title="Private Book",
        )

        response = self.client.get("/api/books/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        books = self.get_results(response)

        self.assertEqual(len(books), 1)
        self.assertEqual(
            books[0]["title"],
            "Alice's Adventures in Wonderland",
        )

    def test_user_can_get_chapters(self):
        response = self.client.get(
            f"/api/chapters/?book={self.book.id}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        chapters = self.get_results(response)

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["title"], "Chapter I")

    def test_user_can_update_progress(self):
        response = self.client.patch(
            f"/api/books/{self.book.id}/progress/",
            {"pages_read": 50},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.book.refresh_from_db()

        self.assertEqual(self.book.pages_read, 50)
        self.assertEqual(self.book.progress, 50)

    def test_user_can_save_word(self):
        response = self.client.post(
            "/api/words/",
            {
                "word": "curious",
                "translation": "допитливий",
                "context": "Alice was curious.",
                "book": self.book.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SavedWord.objects.count(), 1)

    def test_user_cannot_use_other_users_book(self):
        other_book = Book.objects.create(
            owner=self.other_user,
            title="Private Book",
        )

        response = self.client.post(
            "/api/words/",
            {
                "word": "secret",
                "translation": "таємний",
                "book": other_book.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_see_other_users_chapters(self):
        other_book = Book.objects.create(
            owner=self.other_user,
            title="Private Book",
        )

        Chapter.objects.create(
            book=other_book,
            number=1,
            title="Private Chapter",
            content="Private content.",
        )

        response = self.client.get("/api/chapters/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        chapters = self.get_results(response)

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["book"], self.book.id)