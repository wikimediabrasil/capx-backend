from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Message
from users.models import CustomUser
from social_django.models import UserSocialAuth
import secrets

class MessageViewTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.staff_user = CustomUser.objects.create_user(username='staffuser', password=str(secrets.randbits(16)), is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    @patch('message.models.MessageService.send_message', return_value=None)
    def test_list_messages(self, mock_send_message):
        Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.get('/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['message'], 'Sample message')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_create_message(self, mock_send_message):
        response = self.client.post('/messages/', {
            'message': 'Sample message',
            'subject': 'Sample subject',
            'receiver': 'receiver',
            'method': 'email'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().message, 'Sample message')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_update_message(self, mock_send_message):
        message = Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.put(f'/messages/{message.id}/', {
            'message': 'Updated message',
            'subject': 'Updated subject',
            'receiver': 'receiver',
            'method': 'email'
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Message.objects.get().message, 'Sample message')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_delete_message(self, mock_send_message):
        message = Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.delete(f'/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().message, 'Sample message')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_partial_update_message(self, mock_send_message):
        message = Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.patch(f'/messages/{message.id}/', {
            'message': 'Updated message',
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Message.objects.get().message, 'Sample message')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_retrieve_message(self, mock_send_message):
        message = Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.get(f'/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Sample message')
        self.assertEqual(response.data['receiver'], 'receiver')
        self.assertEqual(response.data['method'], 'email')
        self.assertEqual(response.data['status'], 'sending')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_list_messages_staff(self, mock_send_message):
        Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get('/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['message'], 'Sample message')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_create_message_as_another_user(self, mock_send_message):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post('/messages/', {
            'message': 'Sample message',
            'subject': 'Sample subject',
            'receiver': 'receiver',
            'sender': self.user.id,
            'method': 'email'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().message, 'Sample message')
        self.assertEqual(Message.objects.get().sender, self.staff_user)

    def _setup_user_social_auth(self, user):
        """Helper to setup OAuth for a user"""
        return UserSocialAuth.objects.create(
            user=user,
            provider='mediawiki',
            uid='12345678',
            extra_data={
                'access_token': {
                    'oauth_token': 'test_oauth_token',
                    'oauth_token_secret': 'test_oauth_token_secret'
                }
            }
        )

    @patch('message.views.OAuth1Session')
    def test_check_emailable_both_users_emailable(self, mock_oauth):
        """Test when both sender and receiver are emailable"""
        self._setup_user_social_auth(self.user)

        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            # Response for sender check
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': True}]}})),
            # Response for receiver check
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': True}]}}))
        ]

        response = self.client.post('/messages/check_emailable/', {
            'receiver': 'receiver_user'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sender_emailable'], True)
        self.assertEqual(response.data['receiver_emailable'], True)
        self.assertEqual(response.data['can_send_email'], True)

    @patch('message.views.OAuth1Session')
    def test_check_emailable_receiver_not_emailable(self, mock_oauth):
        """Test when receiver is not emailable"""
        self._setup_user_social_auth(self.user)

        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            # Response for sender check (emailable)
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': True}]}})),
            # Response for receiver check (not emailable)
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': False}]}}))
        ]

        response = self.client.post('/messages/check_emailable/', {
            'receiver': 'receiver_user'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sender_emailable'], True)
        self.assertEqual(response.data['receiver_emailable'], False)
        self.assertEqual(response.data['can_send_email'], False)

    @patch('message.views.OAuth1Session')
    def test_check_emailable_sender_not_emailable(self, mock_oauth):
        """Test when sender is not emailable"""
        self._setup_user_social_auth(self.user)

        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            # Response for sender check (not emailable)
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': False}]}})),
            # Response for receiver check (emailable)
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': True}]}}))
        ]

        response = self.client.post('/messages/check_emailable/', {
            'receiver': 'receiver_user'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sender_emailable'], False)
        self.assertEqual(response.data['receiver_emailable'], True)
        self.assertEqual(response.data['can_send_email'], False)

    @patch('message.views.OAuth1Session')
    def test_check_emailable_neither_emailable(self, mock_oauth):
        """Test when neither sender nor receiver are emailable"""
        self._setup_user_social_auth(self.user)

        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            # Response for sender check (not emailable)
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': False}]}})),
            # Response for receiver check (not emailable)
            MagicMock(json=MagicMock(return_value={'query': {'users': [{'emailable': False}]}}))
        ]

        response = self.client.post('/messages/check_emailable/', {
            'receiver': 'receiver_user'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sender_emailable'], False)
        self.assertEqual(response.data['receiver_emailable'], False)
        self.assertEqual(response.data['can_send_email'], False)

    def test_check_emailable_missing_receiver(self):
        """Test when receiver parameter is not provided"""
        self._setup_user_social_auth(self.user)

        response = self.client.post('/messages/check_emailable/', {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    @patch('message.views.OAuth1Session')
    def test_check_emailable_no_oauth(self, mock_oauth):
        """Test when user doesn't have OAuth configured"""
        # Don't setup user social auth

        response = self.client.post('/messages/check_emailable/', {
            'receiver': 'receiver_user'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sender_emailable'], False)
        self.assertEqual(response.data['receiver_emailable'], False)
        self.assertEqual(response.data['can_send_email'], False)

    @patch('message.views.OAuth1Session')
    def test_check_emailable_api_exception(self, mock_oauth):
        """Test when Wikimedia API throws an exception"""
        self._setup_user_social_auth(self.user)

        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = Exception('API Error')

        response = self.client.post('/messages/check_emailable/', {
            'receiver': 'receiver_user'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sender_emailable'], False)
        self.assertEqual(response.data['receiver_emailable'], False)
        self.assertEqual(response.data['can_send_email'], False)
