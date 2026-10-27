from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class TestSyncCampaignsCommand(TestCase):
    def call(self):
        out = StringIO()
        call_command("sync_campaigns", stdout=out, verbosity=1)
        return out.getvalue()

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_successful_fetch(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q1001"},
                        "itemLabel": {"value": "Wiki Loves Monuments"},
                        "itemDescription": {"value": "Annual photo competition"},
                        "minStartDate": {"value": "2024-09-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-09-30T23:59:59Z"},
                    },
                    {
                        "qid": {"value": "Q1002"},
                        "itemLabel": {"value": "Wiki Loves Earth"},
                        "itemDescription": {"value": "Nature photography contest"},
                        "minStartDate": {"value": "2024-05-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-05-31T23:59:59Z"},
                    },
                    {
                        "qid": {"value": "Q1003"},
                        "itemLabel": {"value": "Wiki Loves Africa"},
                        "itemDescription": {
                            "value": "African cultural heritage contest"
                        },
                        "minStartDate": {"value": "2024-02-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-03-31T23:59:59Z"},
                    },
                ]
            }
        }
        mock_get.return_value = mock_response
        output = self.call()

        self.assertIn("Fetching campaigns from Metabase...", output)
        self.assertIn("Found 3 campaigns in Metabase", output)
        self.assertIn("Q1001", output)
        self.assertIn("Q1002", output)
        self.assertIn("Q1003", output)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_empty_results(self, mock_get):
        """Test handling of empty results from Metabase."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_get.return_value = mock_response

        output = self.call()
        self.assertIn("Fetching campaigns from Metabase...", output)
        self.assertIn("No campaigns found in Metabase", output)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_missing_optional_fields(self, mock_get):
        """Test handling of campaigns with missing optional fields (labels, dates, etc.)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q3001"},
                    },
                    {
                        "qid": {"value": "Q3002"},
                        "skillCapXIds": {"value": "123|456"},
                    },
                ]
            }
        }
        mock_get.return_value = mock_response

        output = self.call()
        self.assertIn("Found 2 campaigns in Metabase", output)
        self.assertIn("Q3001", output)
        self.assertIn("Q3002", output)
        self.assertIn("123|456", output)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_http_error(self, mock_get):
        """Test handling of HTTP error from SPARQL endpoint."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        out = StringIO()
        with self.assertRaisesMessage(
            CommandError, "Failed to query Metabase SPARQL endpoint"
        ):
            call_command("sync_campaigns", stdout=out)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_non_200_status(self, mock_get):
        """Test handling of non-200 HTTP status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_get.return_value = mock_response

        out = StringIO()
        with self.assertRaisesMessage(
            CommandError, "Failed to query Metabase SPARQL endpoint"
        ):
            call_command("sync_campaigns", stdout=out)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_qid_extracted_date(self, mock_get):
        """Test that date is extracted"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q99999"},
                        "minStartDate": {"value": "2025-01-01T00:00:00Z"},
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        output = self.call()
        self.assertIn("date(2025, 1, 1)", output)
