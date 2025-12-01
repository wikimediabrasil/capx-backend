from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Message
from users.models import CustomUser
from social_django.models import UserSocialAuth
import secrets

@override_settings(
    SOCIAL_AUTH_MEDIAWIKI_KEY='test_key',
    SOCIAL_AUTH_MEDIAWIKI_SECRET='test_secret'
)

class MessageViewTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.staff_user = CustomUser.objects.create_user(username='staffuser', password=str(secrets.randbits(16)), is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        for u in (self.user, self.staff_user):
            UserSocialAuth.objects.create(
                user=u,
                provider='mediawiki',
                uid=f'{u.username}-uid',
                extra_data={
                    'access_token': {
                        'oauth_token': 'oauth_token',
                        'oauth_token_secret': 'oauth_token_secret'
                    }
                }
            )
    
    def test_list_messages(self):
        Message.objects.create(
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.get('/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['receiver'], 'receiver')
        self.assertEqual(response.data['results'][0]['method'], 'email')
        self.assertEqual(response.data['results'][0]['status'], 'pending')

    @patch('message.services.message_service.OAuth1Session')
    def test_create_message(self, mock_oauth):
        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': True},
                        {'name': 'Testuser', 'emailable': True}
                    ]
                }
            })),
            MagicMock(json=MagicMock(return_value={'query': {'tokens': {'csrftoken': 'test_token'}}}))
        ]
        mock_oauth_instance.post.return_value = MagicMock(json=MagicMock(return_value={'emailuser': {'result': 'Success'}}))

        response = self.client.post('/messages/', {
            'message': 'Sample message',
            'subject': 'Sample subject',
            'receiver': 'receiver',
            'method': 'email'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().status, 'sent')
        # Write-only fields not present in response
        self.assertNotIn('message', response.data)
        self.assertNotIn('subject', response.data)

    def test_update_message(self):
        message = Message.objects.create(
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
        self.assertEqual(Message.objects.get().receiver, 'receiver')

    def test_delete_message(self):
        message = Message.objects.create(
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.delete(f'/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().receiver, 'receiver')

    def test_partial_update_message(self):
        message = Message.objects.create(
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.patch(f'/messages/{message.id}/', {
            'message': 'Updated message',
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Message.objects.get().receiver, 'receiver')

    def test_retrieve_message(self):
        message = Message.objects.create(
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.get(f'/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['receiver'], 'receiver')
        self.assertEqual(response.data['method'], 'email')
        self.assertEqual(response.data['status'], 'pending')
        self.assertNotIn('message', response.data)
        self.assertNotIn('subject', response.data)

    def test_list_messages_staff(self):
        Message.objects.create(
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get('/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['receiver'], 'receiver')
        self.assertEqual(response.data['results'][0]['method'], 'email')
        self.assertEqual(response.data['results'][0]['status'], 'pending')

    @patch('message.services.message_service.OAuth1Session')
    def test_create_message_as_another_user(self, mock_oauth):
        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.get.side_effect = [
            MagicMock(json=MagicMock(return_value={
                'query': {
                    'users': [
                        {'name': 'Receiver', 'emailable': True},
                        {'name': 'Staffuser', 'emailable': True}
                    ]
                }
            })),
            MagicMock(json=MagicMock(return_value={'query': {'tokens': {'csrftoken': 'test_token'}}}))
        ]
        mock_oauth_instance.post.return_value = MagicMock(json=MagicMock(return_value={'emailuser': {'result': 'Success'}}))

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

        # Ensure the sender is the authenticated staff user, not the specified user
        self.assertEqual(Message.objects.get().sender, self.staff_user)
