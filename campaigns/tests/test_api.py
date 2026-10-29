from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign
from skills.models import Skill
from users.models import ProfileCampaign

User = get_user_model()


class CampaignAPITestCase(TestCase):
    """Test cases for Campaign API endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.regular_user = User.objects.create_user(username="A")
        cls.other_user = User.objects.create_user(username="B")
        cls.campaign1 = Campaign.objects.create(
            metabase_qid="Q1001",
            min_start_date="2024-01-01",
            max_end_date="2024-12-31",
        )
        cls.campaign2 = Campaign.objects.create(
            metabase_qid="Q1002",
            min_start_date="2024-06-01",
            max_end_date="2024-06-30",
        )
        cls.campaign3 = Campaign.objects.create(
            metabase_qid="Q1003",
        )
        cls.skill = Skill.objects.create(skill_wikidata_item="Q5001")
        cls.campaign1.skills.add(cls.skill)

    def setUp(self):
        self.client = APIClient()

    def test_list_campaigns_unauthenticated(self):
        """Test listing campaigns without authentication (should work - read-only)."""
        response = self.client.get("/campaigns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_list_campaigns_with_pagination(self):
        """Test campaign list pagination."""
        response = self.client.get("/campaigns/?limit=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn("next", response.data)

    def test_retrieve_campaign(self):
        """Test retrieving a single campaign."""
        response = self.client.get(f"/campaigns/{self.campaign1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["metabase_qid"], "Q1001")
        self.assertIsInstance(response.data["org_qids"], list)
        self.assertIsInstance(response.data["location_qids"], list)
        self.assertIsInstance(response.data["language_qids"], list)
        self.assertIsInstance(response.data["skill_wikidata_qids"], list)

    def test_filter_by_metabase_qid(self):
        """Test filtering campaigns by metabase_qid."""
        response = self.client.get("/campaigns/?metabase_qid=Q1001")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["metabase_qid"], "Q1001")

    def test_filter_by_min_start_date(self):
        """Test filtering by min_start_date."""
        response = self.client.get("/campaigns/?min_start_date=2024-01-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_ordering(self):
        """Test ordering campaigns."""
        response = self.client.get("/campaigns/?ordering=-metabase_qid")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["metabase_qid"], "Q1003")
        self.assertEqual(results[1]["metabase_qid"], "Q1002")
        self.assertEqual(results[2]["metabase_qid"], "Q1001")

    def test_search(self):
        """Test search functionality."""
        response = self.client.get("/campaigns/?search=Q1002")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["metabase_qid"], "Q1002")


class UserCampaignAPITestCase(TestCase):
    """Test cases for User Campaign API endpoints (my_campaigns)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="C")
        cls.other_user = User.objects.create_user(username="D")
        cls.campaign1 = Campaign.objects.create(metabase_qid="Q1001")
        cls.campaign2 = Campaign.objects.create(metabase_qid="Q1002")
        cls.campaign3 = Campaign.objects.create(metabase_qid="Q1003")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_user_campaigns_empty(self):
        """Test listing user campaigns when none are linked."""
        response = self.client.get("/my_campaigns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_user_campaigns_with_data(self):
        """Test listing user campaigns after linking."""
        ProfileCampaign.objects.create(
            profile=self.user.profile,
            campaign=self.campaign1,
            role_wikidata_qid="Q56512863",
        )
        response = self.client.get("/my_campaigns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["metabase_qid"], "Q1001")

    def test_list_user_campaigns_filter_by_role(self):
        """Test filtering user campaigns by role Wikidata QID."""
        ProfileCampaign.objects.create(
            profile=self.user.profile,
            campaign=self.campaign1,
            role_wikidata_qid="Q56512863", # participant
        )
        ProfileCampaign.objects.create(
            profile=self.user.profile,
            campaign=self.campaign2,
            role_wikidata_qid="Q1419997", # producer
        )
        response = self.client.get("/my_campaigns/?role_wikidata_qid=Q56512863")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["metabase_qid"], "Q1001")

        response = self.client.get("/my_campaigns/?role_wikidata_qid=Q1419997")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["metabase_qid"], "Q1002")

        response = self.client.get("/my_campaigns/?role_wikidata_qid=Q999999")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_add_campaign_to_profile(self):
        """Test adding a campaign to user's profile."""
        response = self.client.post(
            "/my_campaigns/",
            {
                "campaign": self.campaign1.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["metabase_qid"], "Q1001")
        profile_campaign = ProfileCampaign.objects.get(
            profile=self.user.profile, campaign=self.campaign1
        )
        self.assertEqual(profile_campaign.role_wikidata_qid, "Q56512863")

    def test_add_campaign_with_custom_role(self):
        """Test adding a campaign with a custom role."""
        response = self.client.post(
            "/my_campaigns/",
            {
                "campaign": self.campaign1.id,
                "role_wikidata_qid": "Q123456",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        profile_campaign = ProfileCampaign.objects.get(
            profile=self.user.profile, campaign=self.campaign1
        )
        self.assertEqual(profile_campaign.role_wikidata_qid, "Q123456")

    def test_add_invalid_role_format(self):
        """Test adding a campaign with invalid role format."""
        response = self.client.post(
            "/my_campaigns/",
            {
                "campaign": self.campaign1.id,
                "role_wikidata_qid": "invalid",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_campaign_without_campaign_field(self):
        """Test adding a campaign without the required campaign field."""
        response = self.client.post("/my_campaigns/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", str(response.data))

    def test_add_nonexistent_campaign(self):
        """Test adding a non-existent campaign."""
        response = self.client.post(
            "/my_campaigns/",
            {
                "campaign": 99999,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Campaign not found", str(response.data))

    def test_add_duplicate_campaign(self):
        """Test adding the same campaign twice."""
        ProfileCampaign.objects.create(
            profile=self.user.profile,
            campaign=self.campaign1,
            role_wikidata_qid="Q56512863",
        )
        response = self.client.post(
            "/my_campaigns/",
            {
                "campaign": self.campaign1.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_remove_campaign_from_profile(self):
        """Test removing a campaign from user's profile."""
        ProfileCampaign.objects.create(
            profile=self.user.profile,
            campaign=self.campaign1,
            role_wikidata_qid="Q56512863",
        )
        response = self.client.delete(f"/my_campaigns/{self.campaign1.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            ProfileCampaign.objects.filter(
                profile=self.user.profile, campaign=self.campaign1
            ).exists()
        )

    def test_remove_nonexistent_campaign(self):
        """Test removing a campaign not linked to user's profile."""
        response = self.client.delete(f"/my_campaigns/{self.campaign1.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_invalid_campaign_id(self):
        """Test removing a campaign with invalid (non-integer) ID."""
        response = self.client.delete("/my_campaigns/invalid/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Campaign not found.")

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access my_campaigns."""
        self.client.force_authenticate(user=None)
        response = self.client.get("/my_campaigns/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
