from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib import admin
from django.test import RequestFactory, TestCase

from skills.admin import SkillAdmin
from skills.models import Skill
from users.models import CustomUser


class SkillAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = SkillAdmin(model=Skill, admin_site=admin.site)
        self.admin.message_user = Mock()
        self.user = CustomUser.objects.create_user(username="staff", password="test")
        self.user.is_staff = True
        self.user.save()

    @patch("skills.admin.MetabaseClient")
    def test_save_model_create_success(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.login_bot.return_value = mock_client
        mock_client.create_item.return_value = {
            "index_term_id": "Q12345",
            "capacity_id": "Q67890",
        }

        request = self.factory.post("/admin/skills/skill/add/")
        request.user = self.user
        form = SimpleNamespace(
            cleaned_data={
                "title": "Test title",
                "description": "Test description",
                "lang": "en",
            }
        )
        obj = Skill(skill_wikidata_item="Q555")

        self.admin.save_model(request, obj, form, change=False)

        created = Skill.objects.get(skill_wikidata_item="Q555")

        mock_client.login_bot.assert_called_once()
        mock_client.create_item.assert_called_once_with(
            label="Test title",
            description="Test description",
            lang="en",
            wikidata_qid="Q555",
            editor_username="staff",
            skill_pk=created.pk,
        )
        self.admin.message_user.assert_called()

    @patch("skills.admin.MetabaseClient")
    def test_save_model_create_failure_rolls_back_local_skill(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.login_bot.return_value = mock_client
        mock_client.create_item.side_effect = RuntimeError("provider error")

        request = self.factory.post("/admin/skills/skill/add/")
        request.user = self.user
        form = SimpleNamespace(
            cleaned_data={
                "title": "Test title",
                "description": "Test description",
                "lang": "en",
            }
        )
        obj = Skill(skill_wikidata_item="Q556")

        self.admin.save_model(request, obj, form, change=False)

        self.assertFalse(Skill.objects.filter(skill_wikidata_item="Q556").exists())
        self.admin.message_user.assert_called()
