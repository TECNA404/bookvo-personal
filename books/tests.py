from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import override_settings
from unittest.mock import patch

from .models import Book

class BooksApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="api_test_user",
            password="strong-test-password",
        )
        self.other_user = User.objects.create_user(
            username="other_test_user",
            password="strong-test-password",
        )

        self.client.force_authenticate(user=self.user)

        self.book_url = "/api/books/"
        self.book = Book.objects.create(
            owner=self.user,
            title="Test Book",
            author="Test Author",
            year=2024,
            genre="fiction",
            pages_total=200,
            pages_read=0,
        )

    def test_books_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.book_url)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_authenticated_user_can_list_own_books(self):
        response = self.client.get(self.book_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_data = response.data

        if isinstance(response_data, dict):
            books = response_data.get(
                "results",
                response_data,
            )
        else:
            books = response_data

        self.assertEqual(len(books), 1)
        self.assertEqual(
            books[0]["title"],
            "Test Book",
        )

    def test_user_cannot_see_another_users_books(self):
        Book.objects.create(
            owner=self.other_user,
            title="Private Other Book",
        )

        response = self.client.get(self.book_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_data = response.data

        if isinstance(response_data, dict):
            books = response_data.get(
                "results",
                response_data,
            )
        else:
            books = response_data

        titles = [book["title"] for book in books]

        self.assertIn("Test Book", titles)
        self.assertNotIn(
            "Private Other Book",
            titles,
        )

    def test_user_can_create_book(self):
        payload = {
            "title": "Created Book",
            "author": "New Author",
            "year": 2025,
            "genre": "science",
            "pages_total": 300,
            "pages_read": 0,
            "status": "planning",
            "notes": "Test notes",
        }

        response = self.client.post(
            self.book_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created_book = Book.objects.get(
            title="Created Book",
        )

        self.assertEqual(
            created_book.owner,
            self.user,
        )
        self.assertEqual(
            created_book.progress,
            0,
        )

    def test_update_progress_calculates_percentage(self):
        url = f"{self.book_url}{self.book.id}/progress/"

        response = self.client.patch(
            url,
            {"pages_read": 100},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.pages_read,
            100,
        )
        self.assertEqual(
            self.book.progress,
            50,
        )
        self.assertEqual(
            self.book.status,
            "planning",
        )

    def test_update_progress_rejects_negative_value(self):
        url = f"{self.book_url}{self.book.id}/progress/"

        response = self.client.patch(
            url,
            {"pages_read": -1},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.pages_read,
            0,
        )

    def test_update_progress_rejects_value_above_total(self):
        url = f"{self.book_url}{self.book.id}/progress/"

        response = self.client.patch(
            url,
            {"pages_read": 201},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_finish_book_sets_full_progress(self):
        url = f"{self.book_url}{self.book.id}/finish/"

        response = self.client.patch(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.status,
            "finished",
        )
        self.assertEqual(
            self.book.progress,
            100,
        )
        self.assertEqual(
            self.book.pages_read,
            self.book.pages_total,
        )

    def test_statistics_returns_book_counts(self):
        Book.objects.create(
            owner=self.user,
            title="Reading Book",
            status="reading",
            progress=50,
        )
        Book.objects.create(
            owner=self.user,
            title="Finished Book",
            status="finished",
            progress=100,
        )

        response = self.client.get(
            f"{self.book_url}statistics/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["total"],
            3,
        )
        self.assertEqual(
            response.data["planning"],
            1,
        )
        self.assertEqual(
            response.data["reading"],
            1,
        )
        self.assertEqual(
            response.data["finished"],
            1,
        )
        self.assertEqual(
            response.data["average_progress"],
            50,
        )

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": (
                    "rest_framework_simplejwt.authentication.JWTAuthentication",
            ),
            "DEFAULT_PERMISSION_CLASSES": (
                    "rest_framework.permissions.IsAuthenticated",
            ),
            "DEFAULT_THROTTLE_CLASSES": [
                "rest_framework.throttling.ScopedRateThrottle",
            ],
            "DEFAULT_THROTTLE_RATES": {
                "translation": "2/minute",
            },
        }
    )
    class TranslationThrottleTests(APITestCase):
        def setUp(self):
            User = get_user_model()

            self.user = User.objects.create_user(
                username="translation_user",
                password="strong-test-password",
            )

            self.client.force_authenticate(user=self.user)

        @patch("books.views.requests.get")
        def test_translation_throttle(self, mock_get):
            mock_get.return_value.ok = True
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {
                "responseData": {
                    "translatedText": "привет",
                },
            }

            url = "/api/translate/?text=hello&target=uk"

            first_response = self.client.get(url)
            second_response = self.client.get(url)
            third_response = self.client.get(url)

            self.assertEqual(
                first_response.status_code,
                status.HTTP_200_OK,
            )
            self.assertEqual(
                second_response.status_code,
                status.HTTP_200_OK,
            )
            self.assertEqual(
                third_response.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )