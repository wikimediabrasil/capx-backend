from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.models import Project, ProjectMember, ProjectMemberAcceptance
from users.models import CustomUser
from orgs.models import Organization, OrganizationType
from skills.models import Skill

import secrets

class ProjectModelTest(TestCase):

    def setUp(self):
        self.user = CustomUser.objects.create_user(username='usertest', password=str(secrets.randbits(16)))
        self.skill = Skill.objects.create(skill_wikidata_item="Q987654321")
        self.organization_type = OrganizationType.objects.create(
            type_code='org',
            type_name='Orgs'
        )
        self.organization = Organization.objects.create(
            display_name='Organization for Testing',
            acronym='OT',
            type=self.organization_type
        )
        self.organization.managers.add(self.user)
        self.project = Project.objects.create(
            display_name='Test Project',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        self.project.related_skills.add(self.skill)

    def test_project_creation(self):
        self.assertEqual(self.project.display_name, 'Test Project')
        self.assertEqual(self.project.profile_image, 'https://commons.wikimedia.org/wiki/File:test.jpg')
        self.assertEqual(self.project.description, 'A test project')
        self.assertEqual(self.project.url, 'https://example.com')
        self.assertEqual(self.project.creator, self.user)
        self.assertIn(self.skill, self.project.related_skills.all())

    def test_invalid_profile_image_url(self):
        self.project.profile_image = 'https://invalid.url'
        with self.assertRaises(ValidationError):
            self.project.full_clean()

    def test_add_project_member(self):
        project_member = ProjectMember.objects.create(
            project=self.project,
            organization=self.organization
        )
        self.assertIn(project_member, self.project.organizations.all())

    def test_add_project_member_acceptance(self):
        project_member = ProjectMember.objects.create(
            project=self.project,
            organization=self.organization
        )
        project_member_acceptance = ProjectMemberAcceptance.objects.create(
            project_member=project_member,
            accepted=True
        )
        self.assertEqual(project_member_acceptance.project_member, project_member)
        self.assertTrue(project_member_acceptance.accepted)
        self.assertIsNotNone(project_member_acceptance.date)

    def test_project_str_method(self):
        self.assertEqual(str(self.project), 'Test Project')