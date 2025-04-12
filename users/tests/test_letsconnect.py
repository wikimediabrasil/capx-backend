from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from users.models import LetsConnectLog
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import json
from json.decoder import JSONDecodeError
import logging

logger = logging.getLogger(__name__)

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
        try:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            logger.info("Private key successfully generated in setUp.")
        except Exception as e:
            logger.error(f"Error generating private key in setUp: {e}")
            raise

    @patch("users.letsconnect.requests.post")
    @patch("users.letsconnect.serialization.load_pem_private_key")
    def test_create_success(self, mock_load_key, mock_post):
        try:
            mock_load_key.return_value = self.private_key
            logger.info("Mock for load_pem_private_key applied successfully.")
        except Exception as e:
            logger.error(f"Error applying mock for load_pem_private_key: {e}")
            raise

        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"confirmation": "12345"})
        )
        logger.info("Mock for requests.post applied successfully.")

        response = self.client.post("/letsconnect/", self.valid_payload, format="json")
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["confirmation"], "12345")
        self.assertTrue(LetsConnectLog.objects.filter(user=self.user, confirmation="12345").exists())

    @patch("users.letsconnect.requests.post")
    @patch("users.letsconnect.serialization.load_pem_private_key")
    def test_create_failure(self, mock_load_key, mock_post):
        try:
            mock_load_key.return_value = self.private_key
            logger.info("Mock for load_pem_private_key applied successfully.")
        except Exception as e:
            logger.error(f"Error applying mock for load_pem_private_key: {e}")
            raise

        mock_post.return_value = MagicMock(
            status_code=400,
            json=MagicMock(return_value={"error": "Invalid data"})
        )
        logger.info("Mock for requests.post applied successfully.")

        response = self.client.post("/letsconnect/", self.valid_payload, format="json")
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["success"], False)
        self.assertEqual(response.data["error"], "Invalid data")

    def test_create_invalid_payload(self):
        response = self.client.post("/letsconnect/", self.invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", response.data)

    @patch("users.letsconnect.serialization.load_pem_private_key")
    def test_create_private_key_missing(self, mock_load_key):
        mock_load_key.side_effect = FileNotFoundError
        logger.info("Simulating FileNotFoundError for private key.")

        response = self.client.post("/letsconnect/", self.valid_payload, format="json")
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["success"], False)
        self.assertEqual(response.data["error"], "Private key not found")

    @patch("users.letsconnect.requests.post")
    def test_process_response_json_decode_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Invalid JSON response"
        mock_response.json.side_effect = JSONDecodeError("Expecting value", "Invalid JSON response", 0)
        mock_post.return_value = mock_response

        response = self.client.post("/letsconnect/", self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["success"], False)
        self.assertEqual(response.data["error"], "Invalid JSON response")