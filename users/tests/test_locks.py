from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.models import CustomUser
import re

class LocksCommandTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='activeuser', password='password', is_active=True)

    @patch('sys.stdout.write')
    @patch('users.management.commands.locks.requests.get')
    def test_handle_locked_user(self, mock_get, mock_stdout):
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

        call_command('locks', verbosity=2)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        expected_text = 'User activeuser is locked and has been deactivated.'
        calls = [call[0][0] for call in mock_stdout.call_args_list]
        found = any(re.search(re.escape(expected_text), c) for c in calls)
        self.assertTrue(
            found,
            f"Expected '{expected_text}' in output, got: {calls}"
        )

    @patch('sys.stdout.write')
    @patch('users.management.commands.locks.requests.get')
    def test_handle_active_user(self, mock_get, mock_stdout):
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

        call_command('locks', verbosity=2)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        expected_text = 'User activeuser is not locked.'
        calls = [call[0][0] for call in mock_stdout.call_args_list]
        found = any(re.search(re.escape(expected_text), c) for c in calls)
        self.assertTrue(
            found,
            f"Expected '{expected_text}' in output, got: {calls}"
        )

    @patch('sys.stdout.write')
    @patch('users.management.commands.locks.requests.get')
    def test_handle_request_error(self, mock_get, mock_stdout):
        mock_get.side_effect = Exception("Request failed")

        call_command('locks', verbosity=2)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)