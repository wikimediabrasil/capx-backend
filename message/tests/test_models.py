from django.test import TestCase
from ..models import Message
from users.models import CustomUser
import secrets


class TestMessageModel(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))

    def test_message_creation(self):
        message = Message.objects.create(
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
        self.assertEqual(expected_status, 'pending')

    def test_message_str(self):
        message = Message.objects.create(
            sender=self.user,
            receiver='receiver',
            method='email'
        )
        expected_str = f'{message.sender} to {message.receiver} - {message.date.strftime("%d/%m/%Y %H:%M:%S")}'

        self.assertEqual(expected_str, str(message))