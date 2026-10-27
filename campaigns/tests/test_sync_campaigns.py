from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from campaigns.models import Campaign


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
                        "minStartDate": {"value": "2024-09-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-09-30T23:59:59Z"},
                        "orgQids": {"value": "Q1|Q2"},
                        "locationQids": {"value": "Q3|Q4"},
                        "languageQids": {"value": "Q5|Q6"},
                        "skillCapXIds": {"value": "123|456"},
                    },
                    {
                        "qid": {"value": "Q1002"},
                        "minStartDate": {"value": "2024-05-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-05-31T23:59:59Z"},
                        "orgQids": {"value": "Q7"},
                        "locationQids": {"value": ""},
                        "languageQids": {"value": "Q8"},
                        "skillCapXIds": {"value": "789"},
                    },
                ]
            }
        }
        mock_get.return_value = mock_response
        output = self.call()

        self.assertIn("Fetching campaigns from Metabase...", output)
        self.assertIn("Found 2 campaigns in Metabase", output)
        self.assertIn("Created: Q1001", output)
        self.assertIn("Created: Q1002", output)
        self.assertIn("Sync complete. Created: 2, Updated: 0", output)

        self.assertEqual(Campaign.objects.count(), 2)

        campaign1 = Campaign.objects.get(metabase_qid="Q1001")
        self.assertEqual(campaign1.metabase_qid, "Q1001")
        self.assertEqual(str(campaign1.min_start_date), "2024-09-01")
        self.assertEqual(str(campaign1.max_end_date), "2024-09-30")
        self.assertEqual(campaign1.org_qids, "Q1|Q2")
        self.assertEqual(campaign1.location_qids, "Q3|Q4")
        self.assertEqual(campaign1.language_qids, "Q5|Q6")
        self.assertEqual(campaign1.skill_capx_ids, "123|456")

        campaign2 = Campaign.objects.get(metabase_qid="Q1002")
        self.assertEqual(campaign2.metabase_qid, "Q1002")
        self.assertEqual(str(campaign2.min_start_date), "2024-05-01")
        self.assertEqual(str(campaign2.max_end_date), "2024-05-31")
        self.assertEqual(campaign2.org_qids, "Q7")
        self.assertEqual(campaign2.location_qids, "")
        self.assertEqual(campaign2.language_qids, "Q8")
        self.assertEqual(campaign2.skill_capx_ids, "789")

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_updates_existing(self, mock_get):
        Campaign.objects.create(
            metabase_qid="Q1001",
            min_start_date="2024-01-01",
            max_end_date="2024-01-31",
            org_qids="OLD|ORG",
            location_qids="OLD|LOC",
            language_qids="OLD|LANG",
            skill_capx_ids="999",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q1001"},
                        "minStartDate": {"value": "2024-09-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-09-30T23:59:59Z"},
                        "orgQids": {"value": "Q1|Q2"},
                        "locationQids": {"value": "Q3|Q4"},
                        "languageQids": {"value": "Q5|Q6"},
                        "skillCapXIds": {"value": "123|456"},
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        output = self.call()

        self.assertIn("Updated: Q1001", output)
        self.assertIn("Sync complete. Created: 0, Updated: 1", output)

        # Verify only one campaign exists and it's updated
        self.assertEqual(Campaign.objects.count(), 1)
        campaign = Campaign.objects.get(metabase_qid="Q1001")
        self.assertEqual(str(campaign.min_start_date), "2024-09-01")
        self.assertEqual(campaign.org_qids, "Q1|Q2")
        self.assertEqual(campaign.skill_capx_ids, "123|456")

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_empty_results(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_get.return_value = mock_response

        output = self.call()
        self.assertIn("Fetching campaigns from Metabase...", output)
        self.assertIn("No campaigns found in Metabase", output)
        self.assertEqual(Campaign.objects.count(), 0)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_missing_optional_fields(self, mock_get):
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
        self.assertEqual(Campaign.objects.count(), 2)

        campaign1 = Campaign.objects.get(metabase_qid="Q3001")
        self.assertIsNone(campaign1.min_start_date)
        self.assertIsNone(campaign1.max_end_date)
        self.assertEqual(campaign1.org_qids, "")
        self.assertEqual(campaign1.skill_capx_ids, "")

        campaign2 = Campaign.objects.get(metabase_qid="Q3002")
        self.assertEqual(campaign2.skill_capx_ids, "123|456")

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_http_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Connection failed")

        out = StringIO()
        with self.assertRaisesMessage(
            CommandError, "Failed to query Metabase SPARQL endpoint"
        ):
            call_command("sync_campaigns", stdout=out)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_non_200_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_get.return_value = mock_response

        out = StringIO()
        with self.assertRaisesMessage(
            CommandError,
            "Failed to query Metabase SPARQL endpoint",
        ):
            call_command("sync_campaigns", stdout=out)
