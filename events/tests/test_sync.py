from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.test import TestCase
from events.models import Events

class TestSyncCommand(TestCase):

    @patch('sys.stdout.write')
    @patch('events.management.commands.sync.requests.get')
    def test_handle_successful_sync(self, mock_get, mock_stdout):
        # Setup mock data
        event = Events.objects.create(
            url="https://learn.wiki/courses/course-123",
            name="Old Event Name",
            time_begin="2023-01-01T00:00:00Z",
            time_end="2023-01-02T00:00:00Z",
            image_url="https://old.image.url"
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "course-123",
            "name": "New Event Name",
            "start": "2023-01-01T12:00:00Z",
            "end": "2023-01-02T12:00:00Z",
            "media": {"image": {"raw": "https://new.image.url"}}
        }
        mock_get.return_value = mock_response

        # Call the command
        call_command('sync', verbosity=2)

        # Refresh the event from the database
        event.refresh_from_db()

        # Assertions
        self.assertEqual(event.name, "New Event Name")
        self.assertEqual(event.time_begin.isoformat(timespec='seconds').replace('+00:00', 'Z'), "2023-01-01T12:00:00Z")
        self.assertEqual(event.time_end.isoformat(timespec='seconds').replace('+00:00', 'Z'), "2023-01-02T12:00:00Z")
        self.assertEqual(event.image_url, "https://new.image.url")
        mock_stdout.assert_called_with("Successfully synced event New Event Name\n")


    @patch('events.management.commands.sync.requests.get')
    def test_handle_invalid_response(self, mock_get):
        # Setup mock data
        event = Events.objects.create(
            url="https://learn.wiki/courses/course-123",
            name="Old Event Name",
            time_begin="2023-01-01T00:00:00Z",
            time_end="2023-01-02T00:00:00Z",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid_key": "invalid_value"}
        mock_get.return_value = mock_response

        # Call the command and assert it raises ValueError
        with self.assertRaises(ValueError):
            call_command('sync')

        # Ensure the event remains unchanged
        event.refresh_from_db()
        self.assertEqual(event.name, "Old Event Name")

    @patch('events.management.commands.sync.requests.get')
    def test_handle_connection_error(self, mock_get):
        # Setup mock data
        Events.objects.create(
            url="https://learn.wiki/courses/course-123",
            time_begin="2023-01-01T00:00:00Z",
            time_end="2023-01-02T00:00:00Z",
        )
        mock_get.return_value.status_code = 500

        # Call the command and assert it raises ConnectionError
        with self.assertRaises(ConnectionError):
            call_command('sync')


