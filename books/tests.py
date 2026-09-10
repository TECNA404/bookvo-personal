from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class BooksApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="api_test_user",
            password="strong-test-password",
        )
        self.token = Token.objects.create(user=self.user)
        self.url = "/api/books/"

    def test_books_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_authenticated_user_can_get_books(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)