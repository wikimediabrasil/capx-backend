from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from campaigns.models import Campaign
from skills.models import Skill


class TestSyncCampaignsCommand(TestCase):
    def call(self):
        out = StringIO()
        call_command("sync_campaigns", stdout=out, verbosity=1)
        return out.getvalue()

    def setUp(self):
        self.skill1 = Skill.objects.create(skill_wikidata_item="Q10001")
        self.skill2 = Skill.objects.create(skill_wikidata_item="Q10002")
        self.skill3 = Skill.objects.create(skill_wikidata_item="Q10003")

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
                        "maxEndDate": {"value": "2024-09-30T00:00:00Z"},
                        "orgQids": {"value": "Q1|Q2"},
                        "locationQids": {"value": "Q3|Q4"},
                        "languageQids": {"value": "Q5|Q6"},
                        "skillCapXIds": {"value": f"{self.skill1.id}|{self.skill2.id}"},
                    },
                    {
                        "qid": {"value": "Q1002"},
                        "minStartDate": {"value": "2024-05-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-05-31T00:00:00Z"},
                        "orgQids": {"value": "Q7"},
                        "locationQids": {"value": ""},
                        "languageQids": {"value": "Q8"},
                        "skillCapXIds": {"value": str(self.skill3.id)},
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
        self.assertEqual(campaign1.skill_capx_ids, f"{self.skill1.id}|{self.skill2.id}")
        self.assertEqual(campaign1.skills.count(), 2)
        self.assertIn(self.skill1, campaign1.skills.all())
        self.assertIn(self.skill2, campaign1.skills.all())

        campaign2 = Campaign.objects.get(metabase_qid="Q1002")
        self.assertEqual(campaign2.metabase_qid, "Q1002")
        self.assertEqual(str(campaign2.min_start_date), "2024-05-01")
        self.assertEqual(str(campaign2.max_end_date), "2024-05-31")
        self.assertEqual(campaign2.org_qids, "Q7")
        self.assertEqual(campaign2.location_qids, "")
        self.assertEqual(campaign2.language_qids, "Q8")
        self.assertEqual(campaign2.skill_capx_ids, str(self.skill3.id))
        self.assertEqual(campaign2.skills.count(), 1)
        self.assertIn(self.skill3, campaign2.skills.all())

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_updates_existing(self, mock_get):
        campaign = Campaign.objects.create(
            metabase_qid="Q1001",
            min_start_date="2024-01-01",
            max_end_date="2024-01-31",
            org_qids="OLD|ORG",
            location_qids="OLD|LOC",
            language_qids="OLD|LANG",
            skill_capx_ids="999",
        )
        campaign.skills.add(self.skill1)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q1001"},
                        "minStartDate": {"value": "2024-09-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-09-30T00:00:00Z"},
                        "orgQids": {"value": "Q1|Q2"},
                        "locationQids": {"value": "Q3|Q4"},
                        "languageQids": {"value": "Q5|Q6"},
                        "skillCapXIds": {"value": f"{self.skill2.id}|{self.skill3.id}"},
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        output = self.call()

        self.assertIn("Updated: Q1001", output)
        self.assertIn("Sync complete. Created: 0, Updated: 1, No changes: 0", output)

        # Verify only one campaign exists and it's updated
        self.assertEqual(Campaign.objects.count(), 1)
        campaign = Campaign.objects.get(metabase_qid="Q1001")
        self.assertEqual(str(campaign.min_start_date), "2024-09-01")
        self.assertEqual(campaign.org_qids, "Q1|Q2")
        self.assertEqual(campaign.skill_capx_ids, f"{self.skill2.id}|{self.skill3.id}")
        self.assertEqual(campaign.skills.count(), 2)
        self.assertIn(self.skill2, campaign.skills.all())
        self.assertIn(self.skill3, campaign.skills.all())
        self.assertNotIn(self.skill1, campaign.skills.all())

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
                        "skillCapXIds": {"value": f"{self.skill1.id}|{self.skill2.id}"},
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
        self.assertEqual(campaign1.skills.count(), 0)

        campaign2 = Campaign.objects.get(metabase_qid="Q3002")
        self.assertEqual(campaign2.skill_capx_ids, f"{self.skill1.id}|{self.skill2.id}")
        self.assertEqual(campaign2.skills.count(), 2)
        self.assertIn(self.skill1, campaign2.skills.all())
        self.assertIn(self.skill2, campaign2.skills.all())

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

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_no_changes(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q1001"},
                        "minStartDate": {"value": "2024-09-01T00:00:00Z"},
                        "maxEndDate": {"value": "2024-09-30T00:00:00Z"},
                        "orgQids": {"value": "Q1|Q2"},
                        "locationQids": {"value": "Q3|Q4"},
                        "languageQids": {"value": "Q5|Q6"},
                        "skillCapXIds": {"value": f"{self.skill1.id}|{self.skill2.id}"},
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        output1 = self.call()
        self.assertIn("Created: Q1001", output1)
        self.assertIn("Sync complete. Created: 1, Updated: 0, No changes: 0", output1)
        output2 = self.call()
        self.assertIn("No changes: Q1001", output2)
        self.assertIn("Sync complete. Created: 0, Updated: 0, No changes: 1", output2)
        self.assertEqual(Campaign.objects.count(), 1)
        campaign = Campaign.objects.get(metabase_qid="Q1001")
        self.assertEqual(campaign.skills.count(), 2)

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_missing_skill(self, mock_get):
        """Test that missing skills are silently skipped, command warns about missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q4001"},
                        "skillCapXIds": {"value": f"{self.skill1.id}|99999|{self.skill2.id}"},
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        output = self.call()

        self.assertIn("Found 1 campaigns in Metabase", output)
        self.assertIn("Created: Q4001", output)
        # Command now warns about missing skills after sync
        self.assertIn("skill(s) not found in database", output)
        self.assertIn("99999", output)

        # Verify campaign was created with only valid skills
        campaign = Campaign.objects.get(metabase_qid="Q4001")
        self.assertEqual(campaign.skills.count(), 2)
        self.assertIn(self.skill1, campaign.skills.all())
        self.assertIn(self.skill2, campaign.skills.all())

    @patch("campaigns.management.commands.sync_campaigns.requests.get")
    def test_handle_invalid_skill_id_format(self, mock_get):
        """Test that invalid skill ID formats are silently skipped, command warns."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "qid": {"value": "Q4002"},
                        "skillCapXIds": {"value": f"{self.skill1.id}|99999|{self.skill2.id}"},
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        output = self.call()

        self.assertIn("Created: Q4002", output)
        # Command warns about missing/invalid skills (99999 is numeric but doesn't exist)
        self.assertIn("skill(s) not found in database", output)
        self.assertIn("99999", output)

        # Verify campaign was created with only valid skills
        campaign = Campaign.objects.get(metabase_qid="Q4002")
        self.assertEqual(campaign.skills.count(), 2)
        self.assertIn(self.skill1, campaign.skills.all())
        self.assertIn(self.skill2, campaign.skills.all())


class TestCampaignModelSyncSkills(TestCase):
    """Test the sync_skills method on the Campaign model directly."""

    def setUp(self):
        self.skill1 = Skill.objects.create(skill_wikidata_item="Q10001")
        self.skill2 = Skill.objects.create(skill_wikidata_item="Q10002")
        self.skill3 = Skill.objects.create(skill_wikidata_item="Q10003")

    def test_sync_skills_all_valid(self):
        """Test sync_skills with all valid skill IDs."""
        campaign = Campaign.objects.create(metabase_qid="Q5001")
        synced = campaign.sync_skills(f"{self.skill1.id}|{self.skill2.id}")

        self.assertEqual(synced, [self.skill1.id, self.skill2.id])
        self.assertEqual(campaign.skills.count(), 2)
        self.assertIn(self.skill1, campaign.skills.all())
        self.assertIn(self.skill2, campaign.skills.all())

    def test_sync_skills_some_missing(self):
        """Test sync_skills with some missing skill IDs."""
        campaign = Campaign.objects.create(metabase_qid="Q5002")
        synced = campaign.sync_skills(f"{self.skill1.id}|99999|{self.skill2.id}")

        # Only valid skills returned
        self.assertEqual(synced, [self.skill1.id, self.skill2.id])
        self.assertEqual(campaign.skills.count(), 2)
        self.assertIn(self.skill1, campaign.skills.all())
        self.assertIn(self.skill2, campaign.skills.all())

    def test_sync_skills_invalid_format(self):
        """Test sync_skills with invalid skill ID format."""
        campaign = Campaign.objects.create(metabase_qid="Q5003")
        synced = campaign.sync_skills(f"{self.skill1.id}|invalid|{self.skill2.id}")

        self.assertEqual(synced, [self.skill1.id, self.skill2.id])
        self.assertEqual(campaign.skills.count(), 2)

    def test_sync_skills_empty_string(self):
        """Test sync_skills with empty string clears skills."""
        campaign = Campaign.objects.create(metabase_qid="Q5004")
        campaign.skills.add(self.skill1, self.skill2)

        synced = campaign.sync_skills("")

        self.assertEqual(synced, [])
        self.assertEqual(campaign.skills.count(), 0)

    def test_sync_skills_none(self):
        """Test sync_skills with None clears skills."""
        campaign = Campaign.objects.create(metabase_qid="Q5005")
        campaign.skills.add(self.skill1)

        synced = campaign.sync_skills(None)

        self.assertEqual(synced, [])
        self.assertEqual(campaign.skills.count(), 0)

    def test_sync_skills_all_missing(self):
        """Test sync_skills when all skill IDs are missing."""
        campaign = Campaign.objects.create(metabase_qid="Q5006")
        synced = campaign.sync_skills("99999|88888")

        self.assertEqual(synced, [])
        self.assertEqual(campaign.skills.count(), 0)

    def test_sync_skills_replaces_existing(self):
        """Test sync_skills replaces existing skills."""
        campaign = Campaign.objects.create(metabase_qid="Q5007")
        campaign.skills.add(self.skill1, self.skill2)

        synced = campaign.sync_skills(str(self.skill3.id))

        self.assertEqual(synced, [self.skill3.id])
        self.assertEqual(campaign.skills.count(), 1)
        self.assertIn(self.skill3, campaign.skills.all())
        self.assertNotIn(self.skill1, campaign.skills.all())
        self.assertNotIn(self.skill2, campaign.skills.all())