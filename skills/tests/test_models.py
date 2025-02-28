from django.test import TestCase
from django.utils import timezone
from skills.models import Skill
from django.core.exceptions import ValidationError

class SkillModelTest(TestCase):
    def test_skill_creation(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )
        self.assertEqual(skill.skill_wikidata_item, "Q123456789")
        self.assertTrue(skill.skill_date_of_creation <= timezone.now())

    def test_skill_str(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )
        self.assertEqual(str(skill), "Q123456789")

    def test_skill_four_levels_deep(self):
        skill1 = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )
        skill2 = Skill.objects.create(
            skill_wikidata_item="Q123456780",
            skill_type=skill1
        )
        skill3 = Skill.objects.create(
            skill_wikidata_item="Q123456781",
            skill_type=skill2
        )
        with self.assertRaises(ValidationError):
            Skill.objects.create(
                skill_wikidata_item="Q123456782",
                skill_type=skill3
            )
