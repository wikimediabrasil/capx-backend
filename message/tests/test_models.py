from django.test import TestCase
from ..models import Message
from users.models import CustomUser
from unittest.mock import patch
import secrets


class TestMessageModel(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_message_creation(self, mock_send_message):
        message = Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        expected_sender = f'{message.sender}'
        expected_receiver = f'{message.receiver}'
        expected_method = f'{message.method}'
        expected_status = f'{message.status}'

        self.assertEqual(expected_sender, 'testuser')
        self.assertEqual(expected_receiver, 'receiver')
        self.assertEqual(expected_method, 'email')
        self.assertEqual(expected_status, 'sending')

    @patch('message.models.MessageService.send_message', return_value=None)
    def test_message_str(self, mock_send_message):
        message = Message.objects.create(
            message='Sample message',
            subject='Sample subject',
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        expected_str = f'{message.sender} to {message.receiver} - {message.date.strftime("%d/%m/%Y %H:%M:%S")}'

        self.assertEqual(expected_str, str(message))