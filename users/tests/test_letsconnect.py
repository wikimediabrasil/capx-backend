from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from users.models import LetsConnectLog
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import json

class TestLetsConnectViewSet(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.client.force_authenticate(user=self.user)
        self.valid_payload = {
            "full_name": "John Doe",
            "email": "johndoe@example.com",
            "role": "Developer",
            "area": "IT",
            "gender": "Male",
            "age": 30,
        }
        self.invalid_payload = {
            "full_name": "",
        }
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

    @patch("users.letsconnect.requests.post")
    @patch("users.letsconnect.serialization.load_pem_private_key")
    def test_create_success(self, mock_load_key, mock_post):
        mock_load_key.return_value = self.private_key
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"confirmation": "12345"})
        )

        response = self.client.post("/letsconnect/", self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["confirmation"], "12345")
        self.assertTrue(LetsConnectLog.objects.filter(user=self.user, confirmation="12345").exists())

    @patch("users.letsconnect.requests.post")
    @patch("users.letsconnect.serialization.load_pem_private_key")
    def test_create_failure(self, mock_load_key, mock_post):
        mock_load_key.return_value = self.private_key
        mock_post.return_value = MagicMock(
            status_code=400,
            json=MagicMock(return_value={"error": "Invalid data"})
        )

        response = self.client.post("/letsconnect/", self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["success"], False)
        self.assertEqual(response.data["error"], "External server failure with code 400")

    def test_create_invalid_payload(self):
        response = self.client.post("/letsconnect/", self.invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", response.data)

    @patch("users.letsconnect.serialization.load_pem_private_key")
    def test_create_private_key_missing(self, mock_load_key):
        mock_load_key.side_effect = FileNotFoundError

        response = self.client.post("/letsconnect/", self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["success"], False)
        self.assertEqual(response.data["error"], "Private key not found")