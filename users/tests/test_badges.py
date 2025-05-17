from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.models import CustomUser
from users.management.commands.badges import Command
from message.models import Message
from django.utils.timezone import now
from datetime import timedelta

class CommandTestCase(TestCase):
    def setUp(self):
        self.command = Command()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpassword',
            email='testuser@example.com'
        )

    @patch('users.management.commands.badges.Message.objects.filter')
    def test_evaluate_logic_sent_messages(self, mock_filter):
        mock_filter.return_value.count.return_value = 5
        result = self.command.evaluate_logic({'target': 'sent_messages', 'value': 10}, self.user)
        self.assertEqual(result, 50.0)

    @patch('users.management.commands.badges.Message.objects.filter')
    def test_evaluate_logic_received_messages(self, mock_filter):
        mock_filter.return_value.count.return_value = 3
        result = self.command.evaluate_logic({'target': 'received_messages', 'value': 10}, self.user)
        self.assertEqual(result, 30.0)

    @patch('users.management.commands.badges.Message.objects.filter')
    def test_evaluate_logic_received_messages_max(self, mock_filter):
        mock_filter.return_value.count.return_value = 3
        result = self.command.evaluate_logic({'target': 'received_messages', 'value': 1}, self.user)
        self.assertEqual(result, 100.0)

    @patch('users.management.commands.badges.Organization.objects.filter')
    def test_evaluate_logic_is_manager(self, mock_filter):
        mock_filter.return_value.exists.return_value = True
        result = self.command.evaluate_logic({'target': 'is_manager', 'value': 10}, self.user)
        self.assertEqual(result, 100.0)

    @patch('users.management.commands.badges.now')
    def test_evaluate_logic_updated_profile(self, mock_now):
        self.user.profile.last_update = now() - timedelta(days=5)
        mock_now.return_value = now()
        result = self.command.evaluate_logic({'target': 'updated_profile', 'value': 10}, self.user)
        self.assertEqual(result, 100.0)

    @patch('users.management.commands.badges.now')
    def test_evaluate_logic_updated_profile_not_updated(self, mock_now):
        self.user.profile.last_update = now() - timedelta(days=15)
        mock_now.return_value = now()
        result = self.command.evaluate_logic({'target': 'updated_profile', 'value': 10}, self.user)
        self.assertEqual(result, 0.0)

    @patch('users.management.commands.badges.CustomUser')
    def test_evaluate_logic_complete_profile(self, mock_user):
        mock_user.profile.territory.exists.return_value = True
        mock_user.profile.affiliation.exists.return_value = True
        mock_user.profile.wikimedia_project.exists.return_value = True
        mock_user.profile.skills_known.exists.return_value = False
        mock_user.profile.skills_available.exists.return_value = False
        mock_user.profile.skills_wanted.exists.return_value = False

        result = self.command.evaluate_logic({'target': 'complete_profile', 'value': 10}, mock_user)
        self.assertEqual(result, 50.0)

    @patch('users.management.commands.badges.now')
    def test_evaluate_logic_account_age(self, mock_now):
        self.user.date_joined = now() - timedelta(days=5)
        mock_now.return_value = now()
        result = self.command.evaluate_logic({'target': 'account_age', 'value': 10}, self.user)
        self.assertEqual(result, 0.0)

    @patch('users.management.commands.badges.now')
    def test_evaluate_logic_account_age_old_enough(self, mock_now):
        self.user.date_joined = now() - timedelta(days=15)
        mock_now.return_value = now()
        result = self.command.evaluate_logic({'target': 'account_age', 'value': 10}, self.user)
        self.assertEqual(result, 100.0)

    @patch('users.management.commands.badges.LetsConnectLog.objects.filter')
    def test_evaluate_logic_lets_connect(self, mock_filter):
        mock_filter.return_value.exists.return_value = True
        result = self.command.evaluate_logic({'target': 'lets_connect', 'value': 10}, self.user)
        self.assertEqual(result, 100.0)

    def test_handle(self):
        with patch('users.management.commands.badges.Badge.objects.all') as mock_badges, \
             patch('users.management.commands.badges.CustomUser.objects.all') as mock_users, \
             patch('users.management.commands.badges.UserBadge.objects.update_or_create') as mock_update_or_create:

            mock_badges.return_value = [MagicMock(logic={'target': 'sent_messages', 'value': 10})]
            mock_users.return_value = [self.user]

            self.command.handle()

            mock_update_or_create.assert_called_once()

    def test_handle_no_logic(self):
        with patch('users.management.commands.badges.Badge.objects.all') as mock_badges, \
             patch('users.management.commands.badges.CustomUser.objects.all') as mock_users, \
             patch('users.management.commands.badges.UserBadge.objects.update_or_create') as mock_update_or_create:

            mock_badges.return_value = [MagicMock(logic=None)]
            mock_users.return_value = [self.user]

            self.command.handle()

            mock_update_or_create.assert_not_called()

