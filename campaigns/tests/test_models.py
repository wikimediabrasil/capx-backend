from django.test import TestCase

from campaigns.models import Campaign


class TestCampaignModelMethods(TestCase):
    def test_get_pipe_separated_as_array_empty(self):
        campaign = Campaign.objects.create(
            metabase_qid="Q1001",
        )
        self.assertEqual(campaign.get_pipe_separated_as_array("org_qids"), [])

    def test_get_all_arrays(self):
        campaign = Campaign.objects.create(
            metabase_qid="Q1001",
            org_qids="Q1|Q2",
            location_qids="Q3",
            language_qids="Q4|Q5|Q6",
            skill_capx_ids="10|20",
        )

        def array(field):
            return campaign.get_pipe_separated_as_array(field)

        self.assertEqual(array("org_qids"), ["Q1", "Q2"])
        self.assertEqual(array("location_qids"), ["Q3"])
        self.assertEqual(array("language_qids"), ["Q4", "Q5", "Q6"])
        self.assertEqual(array("skill_capx_ids"), ["10", "20"])
