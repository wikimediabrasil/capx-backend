from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.models import CustomUser

class LocksCommandTestCase(TestCase):
    def setUp(self):
        self.user_active = CustomUser.objects.create_user(username='activeuser', password='password', is_active=True)
        self.user_locked = CustomUser.objects.create_user(username='lockeduser', password='password', is_active=True)

    @patch('users.management.commands.locks.requests.get')
    def test_handle_locked_user(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'query': {
                'globaluserinfo': {
                    'id': 12345678,
                    'locked': True
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        call_command('locks')

        self.user_locked.refresh_from_db()
        self.assertFalse(self.user_locked.is_active)

    @patch('users.management.commands.locks.requests.get')
    def test_handle_active_user(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'query': {
                'globaluserinfo': {
                    'id': 12345678
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        call_command('locks')

        self.user_active.refresh_from_db()
        self.assertTrue(self.user_active.is_active)

    @patch('users.management.commands.locks.requests.get')
    def test_handle_request_error(self, mock_get):
        mock_get.side_effect = Exception("Request failed")

        call_command('locks')

        self.user_active.refresh_from_db()
        self.user_locked.refresh_from_db()

        self.assertTrue(self.user_active.is_active)
        self.assertTrue(self.user_locked.is_active)