from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from projects.models import Project, ProjectMember, ProjectMemberAcceptance
from orgs.models import Organization, OrganizationType
from users.models import CustomUser
from skills.models import Skill
from rest_framework.test import APIClient
import secrets


class BaseTestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.skill = Skill.objects.create(skill_wikidata_item="Q123456789")
        self.organization_type = OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )
        self.organization = Organization.objects.create(
            display_name='Test Organization',
            acronym='TO',
            type=self.organization_type
        )
        self.organization.managers.add(self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

class ProjectViewSetTests(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_list_projects(self):
        response = self.client.get('/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_project(self):
        data = {
            'display_name': 'New Project',
            'organization': self.organization.id,
            'profile_image': 'https://commons.wikimedia.org/wiki/File:test.jpg',
            'description': 'A test project',
            'url': 'https://example.com',
            'creator': self.user.id,
            'related_skills': [self.skill.id]
        }
        response = self.client.post('/projects/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(Project.objects.get().display_name, 'New Project')
        self.assertEqual(ProjectMember.objects.get().organization, self.organization)
        self.assertEqual(ProjectMemberAcceptance.objects.get().accepted, True)

    def test_create_project_not_manager(self):
        organization2 = Organization.objects.create(
            display_name='Test Organization 2',
            acronym='TO2',
            type=self.organization_type
        )
        data = {
            'display_name': 'New Project',
            'organization': organization2.id,
            'profile_image': 'https://commons.wikimedia.org/wiki/File:test.jpg',
            'description': 'A test project',
            'url': 'https://example.com',
            'creator': self.user.id,
            'related_skills': [self.skill.id]
        }
        response = self.client.post('/projects/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_project(self):
        project = Project.objects.create(
            display_name='Project to update',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        project.related_skills.add(self.skill)
        project_member = ProjectMember.objects.create(project=project, organization=self.organization)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)
        
        data = {
            'display_name': 'Updated Project',
            'organization': self.organization.id,
            'profile_image': 'https://commons.wikimedia.org/wiki/File:test.jpg',
            'description': 'A test project',
            'url': 'https://example.com',
            'creator': self.user.id,
            'related_skills': [self.skill.id]
        }
        response = self.client.put('/projects/1/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Project.objects.get().display_name, 'Updated Project')

    def test_update_project_not_manager(self):
        project = Project.objects.create(
            display_name='Project to update',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        organization2 = Organization.objects.create(
            display_name='Test Organization 2',
            acronym='TO2',
            type=self.organization_type
        )
        project.related_skills.add(self.skill)
        project_member = ProjectMember.objects.create(project=project, organization=organization2)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)
        
        data = {
            'display_name': 'Updated Project',
            'organization': organization2.id,
            'profile_image': 'https://commons.wikimedia.org/wiki/File:test.jpg',
            'description': 'A test project',
            'url': 'https://example.com',
            'creator': self.user.id,
            'related_skills': [self.skill.id]
        }
        response = self.client.put('/projects/1/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_project(self):
        project = Project.objects.create(
            display_name='Project to delete',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        project.related_skills.add(self.skill)
        project_member = ProjectMember.objects.create(project=project, organization=self.organization)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)

        response = self.client.delete('/projects/1/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Project.objects.count(), 0)

    def test_delete_project_not_manager(self):
        project = Project.objects.create(
            display_name='Project to delete',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        organization2 = Organization.objects.create(
            display_name='Test Organization 2',
            acronym='TO2',
            type=self.organization_type
        )
        project.related_skills.add(self.skill)
        project_member = ProjectMember.objects.create(project=project, organization=organization2)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)

        response = self.client.delete('/projects/1/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_project(self):
        project = Project.objects.create(
            display_name='Project to update',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        project.related_skills.add(self.skill)
        project_member = ProjectMember.objects.create(project=project, organization=self.organization)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)

        data = {
            'display_name': 'Updated Project'
        }
        response = self.client.patch('/projects/1/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ProjectMemberViewSetTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            display_name='Test project',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        self.project.related_skills.add(self.skill)

    def test_list_project_members(self):
        response = self.client.get('/project_members/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_project_member(self):
        data = {
            'project': self.project.id,
            'organization': self.organization.id
        }
        response = self.client.post('/project_members/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_project_member_another_organization(self):
        project_member = ProjectMember.objects.create(project=self.project, organization=self.organization)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)
        organization2 = Organization.objects.create(
            display_name='Test Organization 2',
            acronym='TO2',
            type=self.organization_type
        )
        organization2.managers.add(self.user)
        data = {
            'project': self.project.id,
            'organization': organization2.id
        }
        response = self.client.post('/project_members/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_project_member(self):
        project_member = ProjectMember.objects.create(project=self.project, organization=self.organization)
        response = self.client.delete('/project_members/1/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_project_member_another_organization(self):
        project_member = ProjectMember.objects.create(project=self.project, organization=self.organization)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)
        organization2 = Organization.objects.create(
            display_name='Test Organization 2',
            acronym='TO2',
            type=self.organization_type
        )
        organization2.managers.add(self.user)
        project_member2 = ProjectMember.objects.create(project=self.project, organization=organization2)
        ProjectMemberAcceptance.objects.create(project_member=project_member2, accepted=True)

        response = self.client.delete('/project_members/2/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_project_member(self):
        ProjectMember.objects.create(project=self.project, organization=self.organization)
        response = self.client.put('/project_members/1/', {'project': 2})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_project_member(self):
        ProjectMember.objects.create(project=self.project, organization=self.organization)
        response = self.client.patch('/project_members/1/', {'project': 2})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ProjectMemberAcceptanceViewSetTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            display_name='Test project',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        self.project.related_skills.add(self.skill)
        self.project_member = ProjectMember.objects.create(project=self.project, organization=self.organization)

    def test_list_project_member_acceptances(self):
        response = self.client.get('/project_member_acceptance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_project_member_acceptance(self):
        data = {
            'project_member': self.project_member.id,
            'accepted': True
        }
        response = self.client.post('/project_member_acceptance/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProjectMemberAcceptance.objects.count(), 1)
        self.assertTrue(ProjectMemberAcceptance.objects.get().accepted)

    def test_create_project_member_acceptance_already_accepted(self):
        ProjectMemberAcceptance.objects.create(project_member=self.project_member, accepted=True)
        data = {
            'project_member': self.project_member.id,
            'accepted': True
        }
        response = self.client.post('/project_member_acceptance/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_project_member_acceptance_not_manager(self):
        organization2 = Organization.objects.create(
            display_name='Test Organization 2',
            acronym='TO2',
            type=self.organization_type
        )
        project = Project.objects.create(
            display_name='Test project 2',
            profile_image='https://commons.wikimedia.org/wiki/File:test.jpg',
            description='A test project',
            url='https://example.com',
            creator=self.user
        )
        project.related_skills.add(self.skill)
        project_member = ProjectMember.objects.create(project=project, organization=organization2)
        data = {
            'project_member': project_member.id,
            'accepted': True
        }
        response = self.client.post('/project_member_acceptance/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_project_member_acceptance(self):
        ProjectMemberAcceptance.objects.create(project_member=self.project_member, accepted=True)
        response = self.client.put('/project_member_acceptance/1/', {'accepted': False})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_project_member_acceptance(self):
        ProjectMemberAcceptance.objects.create(project_member=self.project_member, accepted=True)
        response = self.client.patch('/project_member_acceptance/1/', {'accepted': False})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_project_member_acceptance(self):
        ProjectMemberAcceptance.objects.create(project_member=self.project_member, accepted=True)
        response = self.client.delete('/project_member_acceptance/1/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)