import pytest
from unittest.mock import MagicMock, patch
from django.utils.timezone import now, timedelta
from users.management.commands.badges import Command

@pytest.fixture
def profile():
    user = MagicMock()
    user.date_joined = now() - timedelta(days=30)
    profile = MagicMock()
    profile.user = user
    profile.updated_at = now() - timedelta(days=10)
    profile.territory.exists.return_value = True
    profile.affiliation.exists.return_value = True
    profile.wikimedia_project.exists.return_value = True
    profile.skills_known.exists.return_value = True
    profile.skills_available.exists.return_value = True
    profile.skills_wanted.exists.return_value = True
    return profile

@pytest.mark.parametrize("target, value, message_count, expected", [
    ('sent_messages', 10, 5, 50),
    ('sent_messages', 10, 20, 100),
    ('sent_messages', 0, 5, 0),
])
@patch('users.management.commands.badges.Message')
def test_evaluate_logic_sent_messages(mock_message, profile, target, value, message_count, expected):
    logic = {'target': target, 'value': value}
    mock_message.objects.filter.return_value.count.return_value = message_count
    cmd = Command()
    result = cmd.evaluate_logic(logic, profile)
    assert result == expected

@pytest.mark.parametrize("target, value, message_count, expected", [
    ('received_messages', 10, 5, 50),
    ('received_messages', 10, 20, 100),
    ('received_messages', 0, 5, 0),
])
@patch('users.management.commands.badges.Message')
def test_evaluate_logic_received_messages(mock_message, profile, target, value, message_count, expected):
    logic = {'target': target, 'value': value}
    mock_message.objects.filter.return_value.count.return_value = message_count
    cmd = Command()
    result = cmd.evaluate_logic(logic, profile)
    assert result == expected

@pytest.mark.parametrize("days_ago, value, expected", [
    (10, 10, 100),
    (5, 10, 50),
    (20, 10, 100),
    (10, 0, 0),
])
def test_evaluate_logic_updated_profile(profile, days_ago, value, expected):
    logic = {'target': 'updated_profile', 'value': value}
    profile.updated_at = now() - timedelta(days=days_ago)
    cmd = Command()
    result = cmd.evaluate_logic(logic, profile)
    assert result == expected

@patch('users.management.commands.badges.Organization')
def test_evaluate_logic_is_manager_true(mock_org, profile):
    logic = {'target': 'is_manager', 'value': 1}
    mock_org.objects.filter.return_value.exists.return_value = True
    cmd = Command()
    assert cmd.evaluate_logic(logic, profile) == 100

@patch('users.management.commands.badges.Organization')
def test_evaluate_logic_is_manager_false(mock_org, profile):
    logic = {'target': 'is_manager', 'value': 1}
    mock_org.objects.filter.return_value.exists.return_value = False
    cmd = Command()
    assert cmd.evaluate_logic(logic, profile) == 0

def test_evaluate_logic_complete_profile_true(profile):
    logic = {'target': 'complete_profile', 'value': 1}
    cmd = Command()
    assert cmd.evaluate_logic(logic, profile) is True

def test_evaluate_logic_complete_profile_false(profile):
    logic = {'target': 'complete_profile', 'value': 1}
    profile.skills_wanted.exists.return_value = False
    cmd = Command()
    assert cmd.evaluate_logic(logic, profile) is False

@pytest.mark.parametrize("days_ago, value, expected", [
    (30, 30, 100),
    (15, 30, 50),
    (60, 30, 100),
    (30, 0, 0),
])
def test_evaluate_logic_account_age(profile, days_ago, value, expected):
    logic = {'target': 'account_age', 'value': value}
    profile.user.date_joined = now() - timedelta(days=days_ago)
    cmd = Command()
    result = cmd.evaluate_logic(logic, profile)
    assert result == expected

@patch('users.management.commands.badges.LetsConnectLog')
def test_evaluate_logic_lets_connect_true(mock_log, profile):
    logic = {'target': 'lets_connect', 'value': 1}
    mock_log.objects.filter.return_value.exists.return_value = True
    cmd = Command()
    assert cmd.evaluate_logic(logic, profile) == 100

@patch('users.management.commands.badges.LetsConnectLog')
def test_evaluate_logic_lets_connect_false(mock_log, profile):
    logic = {'target': 'lets_connect', 'value': 1}
    mock_log.objects.filter.return_value.exists.return_value = False
    cmd = Command()
    assert cmd.evaluate_logic(logic, profile) == 0