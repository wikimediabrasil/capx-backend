import secrets
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from users.views.oauth import AuthView, UserAuthView
from users.models.reference import AuthExtraInfo
from users.models import CustomUser
from unittest.mock import patch

class AuthViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.client.force_authenticate(self.user)

    @patch('social_core.backends.mediawiki.MediaWiki.unauthorized_token', return_value="oauth_token=testtoken&oauth_token_secret=testsecret&oauth_callback_confirmed=true")
    def test_post_with_extra_info(self, mock_unauthorized_token):
        data = {
            'provider': 'mediawiki',
            'extra': 'capx-test.toolforge.org'
        }
        response = self.client.post('/api/login/social/knox/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(AuthExtraInfo.objects.filter(token=response.data['oauth_token']).exists())
        self.assertEqual(AuthExtraInfo.objects.get(token=response.data['oauth_token']).extra, 'capx-test.toolforge.org')

    @patch('social_core.backends.mediawiki.MediaWiki.unauthorized_token', return_value="oauth_token=testtoken&oauth_token_secret=testsecret&oauth_callback_confirmed=true")
    def test_post_with_localhost_port_extra(self, mock_unauthorized_token):
        data = {
            'provider': 'mediawiki',
            'extra': 'localhost:3002'
        }
        response = self.client.post('/api/login/social/knox/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(AuthExtraInfo.objects.filter(token=response.data['oauth_token']).exists())
        self.assertEqual(AuthExtraInfo.objects.get(token=response.data['oauth_token']).extra, 'localhost:3002')

    @patch('social_core.backends.mediawiki.MediaWiki.unauthorized_token', return_value="oauth_token=testtoken&oauth_token_secret=testsecret&oauth_callback_confirmed=true")
    def test_post_with_disallowed_extra_host(self, mock_unauthorized_token):
        data = {
            'provider': 'mediawiki',
            'extra': 'evil.example.org'
        }
        response = self.client.post('/api/login/social/knox/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertFalse(AuthExtraInfo.objects.filter(token='testtoken').exists())

    @patch('social_core.backends.mediawiki.MediaWiki.unauthorized_token', return_value="oauth_token=testtoken&oauth_token_secret=testsecret&oauth_callback_confirmed=true")
    def test_post_without_extra_info(self, mock_unauthorized_token):
        data = {
            'provider': 'mediawiki'
        }
        response = self.client.post('/api/login/social/knox/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(AuthExtraInfo.objects.filter(token=response.data['oauth_token']).exists())

class UserAuthViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.client.force_authenticate(self.user)
        self.auth_extra_info = AuthExtraInfo.objects.create(token='testtoken', extra='some_extra_info')

    @patch('social_core.backends.mediawiki.MediaWiki.access_token', return_value={
        "oauth_token": "oauth_token_key",
        "oauth_token_secret": "oauth_token_secret",
    })
    @patch('social_core.backends.mediawiki.MediaWiki.get_user_details', return_value={
        "username": "testuser",
        "userID": "12345",
        "email": "testuser@example.com",
        "confirmed_email": True,
        "editcount": 100,
        "rights": ["read", "write"],
        "groups": ["user", "editor"],
        "registered": "2020-01-01T00:00:00Z",
        "blocked": False,
    })
    def test_post_with_valid_token(self, mock_access_token, mock_get_user_details):
        data = {
            'provider': 'mediawiki',
            'oauth_token': 'testtoken',
            'oauth_secret': 'testsecret',
            'oauth_verifier': 'testverifier'
        }
        response = self.client.post('/api/login/social/knox_user/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['extra'], 'some_extra_info')

    @patch('social_core.backends.mediawiki.MediaWiki.access_token', return_value={
        "oauth_token": "oauth_token_key",
        "oauth_token_secret": "oauth_token_secret",
    })
    @patch('social_core.backends.mediawiki.MediaWiki.get_user_details', return_value={
        "username": "testuser",
        "userID": "12345",
        "email": "testuser@example.com",
        "confirmed_email": True,
        "editcount": 100,
        "rights": ["read", "write"],
        "groups": ["user", "editor"],
        "registered": "2020-01-01T00:00:00Z",
        "blocked": False,
    })
    def test_post_with_invalid_token(self, mock_access_token, mock_get_user_details):
        data = {
            'provider': 'mediawiki',
            'oauth_token': 'invalidtoken',
            'oauth_secret': 'testsecret',
            'oauth_verifier': 'testverifier'
        }
        response = self.client.post('/api/login/social/knox_user/', data, format='json')
        self.assertNotIn('extra', response.data)


class CheckViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.client.force_authenticate(self.user)
        self.auth_extra_info = AuthExtraInfo.objects.create(token='testtoken', extra='some_extra_info')

    def test_post_with_existing_token(self):
        data = {
            'oauth_token': 'testtoken'
        }
        response = self.client.post('/api/login/social/check/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['exists'])
        self.assertEqual(response.data['extra'], 'some_extra_info')

    def test_post_with_non_existing_token(self):
        data = {
            'oauth_token': 'nonexistingtoken'
        }
        response = self.client.post('/api/login/social/check/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['exists'])
        self.assertIsNone(response.data['extra'])

    def test_post_without_token(self):
        data = {}
        response = self.client.post('/api/login/social/check/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'oauth_token is required')
