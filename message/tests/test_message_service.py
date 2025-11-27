from django.test import TestCase, override_settings
from django.conf import settings
from unittest.mock import patch, MagicMock
from message.services.message_service import MessageService
from social_django.models import UserSocialAuth
from message.models import Message
from users.models import CustomUser
import secrets

@override_settings(
    SOCIAL_AUTH_MEDIAWIKI_KEY='test_key',
    SOCIAL_AUTH_MEDIAWIKI_SECRET='test_secret'
)

class MessageServiceTest(TestCase):
    def setUp(self):
        self.sender = CustomUser.objects.create_user(username='sender', password=str(secrets.randbits(16)))
        self.receiver = 'receiver'
        self.message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            message='Test message',
            subject='Test subject',
            method='email'
        )
        self.user_social_auth = UserSocialAuth.objects.create(
            user=self.sender,
            provider='mediawiki',
            uid='12345678',
            extra_data={
                'access_token': {
                    'oauth_token': 'test_oauth_token',
                    'oauth_token_secret': 'test_oauth_token_secret'
                }
            }
        )

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_invalid_receiver(self, mock_oauth):
        # First GET: users info (batch) — receiver invalid/missing
        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'missing': True},
                        {'name': 'Sender', 'emailable': True}
                    ]
                }
            }))
        ]

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'failed')
        self.assertEqual(self.message.error_message, 'Receiver account is invalid or does not exist.')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_invalid_sender(self, mock_oauth):
        # First GET: users info (batch) — sender invalid/missing
        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': True},
                        {'name': 'Sender', 'missing': True}
                    ]
                }
            }))
        ]

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'failed')
        self.assertEqual(self.message.error_message, 'An exception occurred: Sender account is invalid or does not exist.')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_user_social_auth_does_not_exist(self, mock_oauth):
        self.user_social_auth.delete()

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'failed')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_exception(self, mock_oauth):
        mock_oauth.side_effect = Exception('Test exception')

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'failed')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_error_fetch_csrf_token(self, mock_oauth):
        mock_oauth_instance = mock_oauth.return_value
        # First GET: users info; Second GET: tokens (None)
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': True},
                        {'name': 'Sender', 'emailable': True}
                    ]
                }
            })),
            MagicMock(json=MagicMock(return_value={'query': {'tokens': {'csrftoken': None}}}))
        ]

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'failed')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_success_email(self, mock_oauth):
        mock_oauth_instance = mock_oauth.return_value
        # First GET: users info (both emailable); Second GET: token
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': True},
                        {'name': 'Sender', 'emailable': True}
                    ]
                }
            })),
            MagicMock(json=MagicMock(return_value={'query': {'tokens': {'csrftoken': 'test_token'}}}))
        ]
        mock_oauth_instance.post.return_value = MagicMock(json=MagicMock(return_value={'emailuser': {'result': 'Success'}}))

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'sent')
        self.assertEqual(self.message.error_message, '')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_success_talk_page(self, mock_oauth):
        self.message.method = 'talkpage'
        self.message.save()

        mock_oauth_instance = mock_oauth.return_value
        # Still fetches users info first even for talk page; then token
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': False},
                        {'name': 'Sender', 'emailable': True}
                    ]
                }
            })),
            MagicMock(json=MagicMock(return_value={'query': {'tokens': {'csrftoken': 'test_token'}}}))
        ]
        mock_oauth_instance.post.return_value = MagicMock(json=MagicMock(return_value={'edit': {'result': 'Success'}}))

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'sent')
        self.assertEqual(self.message.error_message, '')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_receiver_not_emailable_fallback_to_talk_page(self, mock_oauth):
        mock_oauth_instance = mock_oauth.return_value
        # First GET: users info with receiver not emailable; Second GET: token
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': False},
                        {'name': 'Sender', 'emailable': True}
                    ]
                }
            })),
            MagicMock(json=MagicMock(return_value={'query': {'tokens': {'csrftoken': 'test_token'}}}))
        ]
        mock_oauth_instance.post.return_value = MagicMock(json=MagicMock(return_value={'edit': {'result': 'Success'}}))

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'sent')
        self.assertEqual(self.message.error_message, 'Receiver is not emailable. Using talk page instead.')

    @patch('message.services.message_service.OAuth1Session')
    def test_send_message_sender_not_emailable_fallback_to_talk_page(self, mock_oauth):
        mock_oauth_instance = mock_oauth.return_value
        # First GET: users info with sender not emailable; Second GET: token
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': True},
                        {'name': 'Sender', 'emailable': False}
                    ]
                }
            })),
            MagicMock(json=MagicMock(return_value={'query': {'tokens': {'csrftoken': 'test_token'}}}))
        ]
        mock_oauth_instance.post.return_value = MagicMock(json=MagicMock(return_value={'edit': {'result': 'Success'}}))

        MessageService.send_message(self.message)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'sent')
        self.assertEqual(self.message.error_message, 'Sender is not emailable. Using talk page instead.')
    
    @patch('message.services.message_service.OAuth1Session')
    def test_fetch_users_info_missing_name_raises_value_error(self, mock_oauth):
        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.return_value = MagicMock(json=MagicMock(return_value={
            'query': {
                'users': [
                    {'emailable': True}
                ]
            }
        }))
        url = 'https://meta.wikimedia.org/w/api.php'
        with self.assertRaises(ValueError):
            MessageService._fetch_users_info(mock_oauth_instance, url, ['Alice', 'Bob'])
