from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Message
from users.models import CustomUser
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
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        response = self.client.put(f'/messages/{message.id}/', {
            'message': 'Updated message',
            'receiver': 'receiver',
            'method': 'email'
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Message.objects.get().message, 'Sample message')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_delete_message(self, mock_send_message):
        message = Message.objects.create(
            message='Sample message',
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
            'receiver': 'receiver',
            'sender': self.user.id,
            'method': 'email'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().message, 'Sample message')
        self.assertEqual(Message.objects.get().sender, self.staff_user)
