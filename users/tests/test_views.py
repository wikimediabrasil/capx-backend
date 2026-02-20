import profile
import secrets
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from users.models import Profile, CustomUser, LanguageProficiency, SavedItem, Badge, UserBadge
from users.models import Territory, Language, WikimediaProject
from users.serializers import ProfileSerializer, TerritorySerializer, LanguageSerializer, WikimediaProjectSerializer, SavedItemSerializer, BadgeSerializer, UserBadgeSerializer
from skills.models import Skill
from orgs.models import Organization, OrganizationType, OrganizationName
from events.models import Events
from projects.models import Project
from django.utils import timezone
from users.models import Profile, CustomUser
from message.models import Message
from unittest.mock import patch

class ProfileViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_users_list(self):
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles, many=True)
        self.assertEqual(response.data['results'], serializer.data)

    def test_get_profile_detail(self):
        response = self.client.get('/profile/' + str(self.user.pk) + '/')
        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles.first())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_update_profile(self):
        url = '/profile/' + str(self.user.pk) + '/'
        updated_data = {
            'user': {},
            'language': [],
            'about': 'first user ever!',
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles.first())
        self.assertEqual(serializer.data['about'], updated_data['about'])

    def test_destroy_profile(self):
        response = self.client.delete('/profile/' + str(self.user.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_profile(self):
        response = self.client.post('/profile/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_other_profile(self):
        user = CustomUser.objects.create_user(username='test2', password=str(secrets.randbits(16)))
        self.assertNotEqual(user.pk, self.user.pk)

        url = '/profile/' + str(user.pk) + '/'
        updated_data = {
            'user': {},
            'about': 'second user ever!',
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_unmatch_skills_profile(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )

        url = '/profile/' + str(self.user.pk) + '/'
        updated_data = {
            'user': {},
            'skills_available': [str(skill.pk)],
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_match_skills_profile(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )

        url = '/profile/' + str(self.user.pk) + '/'
        updated_data = {
            'user': {},
            'language': [],
            'skills_known': [str(skill.pk)],
            'skills_available': [str(skill.pk)],
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_no_skill_provided(self):
        url = '/profile/' + str(self.user.pk) + '/'
        updated_data = {
            'user': {},
            'language': [],
            'skills_known': [],
            'skills_available': [],
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_find_user_by_username(self):
        response = self.client.get('/users/?username=test')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles, many=True)
        self.assertEqual(response.data['results'], serializer.data)

    def test_update_language_proficiency(self):
        language = Language.objects.create(language_name="Spanish", language_code="es")
        url = '/profile/' + str(self.user.pk) + '/'
        data = self.client.get(url).data
        self.assertEqual(data['language'], [])

        data['language'] = [{'id': language.id, 'proficiency': '3'}]
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        lang_prof = LanguageProficiency.objects.get(profile=self.user.profile, language=language)
        self.assertEqual(lang_prof.proficiency, '3')

    def test_update_too_many_language_proficiency(self):
        # Create 21 languages
        languages = [Language.objects.create(language_name=f"Language {i}", language_code=f"lang{i}") for i in range(21)]
        url = '/profile/' + str(self.user.pk) + '/'
        data = self.client.get(url).data
        self.assertEqual(data['language'], [])
        data['language'] = [{'id': lang.id, 'proficiency': '3'} for lang in languages]
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_too_many_territory(self):
        # Create 11 territories
        territories = [Territory.objects.create(territory_name=f"Territory {i}") for i in range(11)]
        url = '/profile/' + str(self.user.pk) + '/'
        data = self.client.get(url).data
        self.assertEqual(data['territory'], [])
        data['territory'] = [territory.id for territory in territories]
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_too_many_affiliation(self):
        # Create 11 organizations
        organizations = [Organization.objects.create(acronym=f"Org{i}") for i in range(11)]
        url = '/profile/' + str(self.user.pk) + '/'
        data = self.client.get(url).data
        self.assertEqual(data['affiliation'], [])
        data['affiliation'] = [organization.id for organization in organizations]
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_profile_automated_lets_connect_cannot_be_false(self):
        profile = Profile.objects.get(user=self.user)
        profile.automated_lets_connect = True
        profile.save()
        url = '/profile/' + str(self.user.pk) + '/'
        data = {
            'user': {},
            'language': [],
            'automated_lets_connect': False,
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('automated_lets_connect cannot be set to False', response.data['message'])


class QuickListViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()

    def test_list_unauthenticated(self):
        response = self.client.get('/list/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_authenticated_unespecific(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/list/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_invalid(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/list/invalid/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})
        
    def test_list_orgs(self):
        test_org_type = OrganizationType.objects.create(type_name='Type 1', type_code='TYPE1')
        test_territory = Territory.objects.create(territory_name='Territory 1')
        self.client.force_authenticate(self.user)

        organization = Organization.objects.create(
            acronym='NO',
            type=test_org_type,
        )
        OrganizationName.objects.create(
            organization=organization,
            language_code='en',
            name='New Organization'
        )
        organization.territory.set([test_territory])
        other_organization = Organization.objects.create(
            acronym='NO2', 
            type=test_org_type,
        )
        OrganizationName.objects.create(
            organization=other_organization,
            language_code='en',
            name='Another Organization'
        )
        other_organization.territory.set([test_territory])
        organizations = Organization.objects.all()
        # Expect only the English name (no acronym suffix) per simplified __str__
        expected_data = {
            organization.pk: organization.i18n_names.filter(language_code='en').first().name
            for organization in organizations
        }
        response = self.client.get('/list/affiliation/')
        self.assertEqual(response.data, expected_data)

    def test_list_territories(self):
        Territory.objects.create(territory_name='test')
        Territory.objects.create(territory_name='test2')
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/territory/')
        territories = Territory.objects.all()
        expected_data = {territory.pk: territory.territory_name for territory in territories}
        self.assertEqual(response.data, expected_data)

    def test_list_languages(self):
        Language.objects.create(language_name='test', language_code='test')
        Language.objects.create(language_name='test2', language_code='test2')
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/language/')
        languages = Language.objects.all()
        expected_data = {language.pk: language.language_name for language in languages}
        self.assertEqual(response.data, expected_data)

    def test_list_wikimedia_projects(self):
        WikimediaProject.objects.create(wikimedia_project_name='test', wikimedia_project_code='test')
        WikimediaProject.objects.create(wikimedia_project_name='test2', wikimedia_project_code='test2')
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/wikimedia_project/')
        wikimedia_projects = WikimediaProject.objects.all()
        expected_data = {wikimedia_project.pk: wikimedia_project.wikimedia_project_name for wikimedia_project in wikimedia_projects}
        self.assertEqual(response.data, expected_data)

    def test_list_skills(self):
        Skill.objects.create(skill_wikidata_item='Q123')
        Skill.objects.create(skill_wikidata_item='Q321')
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/skills/')
        skills = Skill.objects.all()
        expected_data = {skill.pk: skill.skill_wikidata_item for skill in skills}
        self.assertEqual(response.data, expected_data)

    def test_list_event(self):
        test_org_type = OrganizationType.objects.create(type_name='Type 1', type_code='TYPE1')
        organization = Organization.objects.create(
            acronym='NO',
            type=test_org_type,
        )

        Events.objects.create(
            name='Sample Event',
            type_of_location='virtual',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            creator=self.user,
            organization=organization
        )
        Events.objects.create(
            name='Sample Event 2',
            type_of_location='virtual',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            creator=self.user,
            organization=organization
        )
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/event/')
        events = Events.objects.all()
        expected_data = {event.pk: event.name for event in events}
        self.assertEqual(response.data, expected_data)

    def test_list_project(self):
        Project.objects.create(display_name='Sample Project')
        Project.objects.create(display_name='Sample Project 2')
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/project/')
        projects = Project.objects.all()
        expected_data = {project.pk: project.display_name for project in projects}
        self.assertEqual(response.data, expected_data)

    def test_list_badges(self):
        Badge.objects.create(name='Sample Badge')
        Badge.objects.create(name='Sample Badge 2')
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/badges/')
        badges = Badge.objects.all()
        expected_data = {badge.pk: badge.name for badge in badges}
        self.assertEqual(response.data, expected_data)

    def test_list_users(self):
        self.client.force_authenticate(self.user)

        response = self.client.get('/list/users/')
        users = CustomUser.objects.all()
        expected_data = {user.pk: user.username for user in users}
        self.assertEqual(response.data, expected_data)


class UsersBySkillTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_users_by_skill(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )
        profile = Profile.objects.get(user=self.user)
        profile.skills_known.add(skill)

        response = self.client.get('/users_by_skill/' + str(skill.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.data['known']
        serializer_data = ProfileSerializer(Profile.objects.filter(skills_known=skill), many=True).data
        simplified_serializer_data = [
            {
                'id': profile['user']['id'],
                'display_name': profile['display_name'],
                'username': profile['user']['username'],
                'avatar': profile['avatar']
            } for profile in serializer_data
        ]
        self.assertEqual(response_data, simplified_serializer_data)
    
    def test_get_users_by_skill_no_id(self):
        response = self.client.get('/users_by_skill/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_users_by_skill_not_found(self):
        response = self.client.get('/users_by_skill/0/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_users_by_skill_no_users(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )

        response = self.client.get('/users_by_skill/' + str(skill.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'known': [], 'available': [], 'wanted': []})

class UsersByTagTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_users_by_tag_no_tag_type(self):
        response = self.client.get('/tags/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_users_by_tag_no_tag_id(self):
        response = self.client.get('/tags/a/0/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_users_by_tag_skill(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )
        profile = Profile.objects.get(user=self.user)
        profile.skills_known.add(skill)
        profile.skills_available.add(skill)
        profile.skills_wanted.add(skill)

        skill_versions = ['skill_known', 'skill_available', 'skill_wanted']

        for version in skill_versions:
            response = self.client.get('/tags/' + version + '/' + str(skill.pk) + '/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.data
            serializer_data = ProfileSerializer(Profile.objects.filter(skills_known=skill), many=True).data
            simplified_serializer_data = [
                {
                    'id': profile['user']['id'],
                    'display_name': profile['display_name'],
                    'username': profile['user']['username'],
                    'avatar': profile['avatar']
                } for profile in serializer_data
            ]
            self.assertEqual(response_data, simplified_serializer_data)

    def test_get_users_by_tag_skill_no_id(self):
        response = self.client.get('/tags/skill_known/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_users_by_tag_skill_not_found(self):
        response = self.client.get('/tags/skill_known/999/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_users_by_tag_skill_no_users(self):
        skill = Skill.objects.create(
            skill_wikidata_item="Q123456789"
        )

        response = self.client.get('/tags/skill_known/' + str(skill.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_users_by_tag_language(self):
        language = Language.objects.create(
            language_name='test',
            language_code='test'
        )
        profile = Profile.objects.get(user=self.user)
        lang_prof = LanguageProficiency.objects.create(profile=profile, language=language, proficiency='3')

        response = self.client.get('/tags/language/' + str(language.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.data
        serializer_data = ProfileSerializer(Profile.objects.filter(languageproficiency=lang_prof), many=True).data
        simplified_serializer_data = [
            {
                'id': profile['user']['id'],
                'display_name': profile['display_name'],
                'username': profile['user']['username'],
                'avatar': profile['avatar']
            } for profile in serializer_data
        ]
        self.assertEqual(response_data, simplified_serializer_data)

    def test_get_users_by_tag_language_no_id(self):
        response = self.client.get('/tags/language/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_users_by_tag_language_not_found(self):
        response = self.client.get('/tags/language/999/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_users_by_tag_language_no_users(self):
        language = Language.objects.create(
            language_name='test',
            language_code='test'
        )

        response = self.client.get('/tags/language/' + str(language.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_users_by_tag_territory(self):
        territory = Territory.objects.create(
            territory_name='test'
        )
        profile = Profile.objects.get(user=self.user)
        profile.territory.set([territory])

        response = self.client.get('/tags/territory/' + str(territory.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.data
        serializer_data = ProfileSerializer(Profile.objects.filter(territory=territory), many=True).data
        simplified_serializer_data = [
            {
                'id': profile['user']['id'],
                'display_name': profile['display_name'],
                'username': profile['user']['username'],
                'avatar': profile['avatar']
            } for profile in serializer_data
        ]
        self.assertEqual(response_data, simplified_serializer_data)

    def test_get_users_by_tag_territory_no_id(self):
        response = self.client.get('/tags/territory/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_users_by_tag_territory_not_found(self):
        response = self.client.get('/tags/territory/999/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_users_by_tag_territory_no_users(self):
        territory = Territory.objects.create(
            territory_name='test'
        )

        response = self.client.get('/tags/territory/' + str(territory.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
    
    def test_get_users_by_tag_wikimedia_project(self):
        wikimedia_project = WikimediaProject.objects.create(
            wikimedia_project_name='test',
            wikimedia_project_code='test'
        )
        profile = Profile.objects.get(user=self.user)
        profile.wikimedia_project.set([wikimedia_project])

        response = self.client.get('/tags/wikimedia_project/' + str(wikimedia_project.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.data
        serializer_data = ProfileSerializer(Profile.objects.filter(wikimedia_project=wikimedia_project), many=True).data
        simplified_serializer_data = [
            {
                'id': profile['user']['id'],
                'display_name': profile['display_name'],
                'username': profile['user']['username'],
                'avatar': profile['avatar']
            } for profile in serializer_data
        ]
        self.assertEqual(response_data, simplified_serializer_data)

    def test_get_users_by_tag_wikimedia_project_no_id(self):
        response = self.client.get('/tags/wikimedia_project/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_users_by_tag_wikimedia_project_not_found(self):
        response = self.client.get('/tags/wikimedia_project/999/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_users_by_tag_wikimedia_project_no_users(self):
        wikimedia_project = WikimediaProject.objects.create(
            wikimedia_project_name='test',
            wikimedia_project_code='test'
        )

        response = self.client.get('/tags/wikimedia_project/' + str(wikimedia_project.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_users_by_tag_invalid_tag_type(self):
        response = self.client.get('/tags/invalid/1/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_users_by_tag_invalid_tag_id(self):
        response = self.client.get('/tags/skill/invalid/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_users_by_tag_affiliation(self):
        organization = Organization.objects.create(
            acronym='NO'
        )
        OrganizationName.objects.create(organization=organization, name='New Organization', language_code='en')
        profile = Profile.objects.get(user=self.user)
        profile.affiliation.set([organization])

        response = self.client.get('/tags/affiliation/' + str(organization.pk) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.data
        serializer_data = ProfileSerializer(Profile.objects.filter(affiliation=organization), many=True).data
        simplified_serializer_data = [
            {
                'id': profile['user']['id'],
                'display_name': profile['display_name'],
                'username': profile['user']['username'],
                'avatar': profile['avatar']
            } for profile in serializer_data
        ]
        self.assertEqual(response_data, simplified_serializer_data)

class UsersFilterTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_filter_by_territory(self):
        self.territory = Territory.objects.create(territory_name='Territory 1')
        self.child_territory = Territory.objects.create(territory_name='Child Territory 1')
        self.child_territory.parent_territory.set([self.territory])
        self.user.profile.territory.set([self.child_territory])

        response = self.client.get(f'/users/?territory={self.territory.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_skills_known_true(self):
        skill = Skill.objects.create(skill_wikidata_item="Q123456789")
        profile = Profile.objects.get(user=self.user)
        profile.skills_known.add(skill)

        response = self.client.get('/users/', {'has_skills_known': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_skills_known_false(self):
        response = self.client.get('/users/', {'has_skills_known': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_skills_available_true(self):
        skill = Skill.objects.create(skill_wikidata_item="Q123456789")
        profile = Profile.objects.get(user=self.user)
        profile.skills_available.add(skill)

        response = self.client.get('/users/', {'has_skills_available': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_skills_available_false(self):
        response = self.client.get('/users/', {'has_skills_available': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_skills_wanted_true(self):
        skill = Skill.objects.create(skill_wikidata_item="Q123456789")
        profile = Profile.objects.get(user=self.user)
        profile.skills_wanted.add(skill)

        response = self.client.get('/users/', {'has_skills_wanted': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_skills_wanted_false(self):
        response = self.client.get('/users/', {'has_skills_wanted': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_any_skills_true(self):
        skill = Skill.objects.create(skill_wikidata_item="Q123456789")
        profile = Profile.objects.get(user=self.user)
        profile.skills_known.add(skill)

        response = self.client.get('/users/', {'has_any_skills': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_any_skills_false(self):
        response = self.client.get('/users/', {'has_any_skills': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class UsersNameSearchTestCase(TestCase):
    def setUp(self):
        self.user1 = CustomUser.objects.create_user(username='albertoleoncio', password=str(secrets.randbits(16)))
        self.user1.profile.display_name = 'Alberto Leoncio'
        self.user1.profile.save()
        
        self.user2 = CustomUser.objects.create_user(username='johndoe', password=str(secrets.randbits(16)))
        self.user2.profile.display_name = 'John Doe'
        self.user2.profile.save()
        
        self.user3 = CustomUser.objects.create_user(username='marialeonardo', password=str(secrets.randbits(16)))
        self.user3.profile.display_name = 'Maria Da Silva'
        self.user3.profile.save()
        
        self.user4 = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.user4.profile.display_name = 'Test User'
        self.user4.profile.save()
        
        self.client = APIClient()
        self.client.force_authenticate(self.user1)

    def test_search_by_name_partial_match_username(self):
        # Search for "leo" should match usernames containing "leo"
        response = self.client.get('/users/', {'name': 'leo'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [result['user']['username'] for result in response.data['results']]
        self.assertIn('albertoleoncio', usernames)
        self.assertIn('marialeonardo', usernames)
        self.assertEqual(len(response.data['results']), 2)

    def test_search_by_name_full_match_username(self):
        # Search for "alberto" should match username "albertoleoncio"
        response = self.client.get('/users/', {'name': 'alberto'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [result['user']['username'] for result in response.data['results']]
        self.assertIn('albertoleoncio', usernames)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_name_case_insensitive(self):
        # Search should be case-insensitive
        response = self.client.get('/users/', {'name': 'JOHN'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [result['user']['username'] for result in response.data['results']]
        self.assertIn('johndoe', usernames)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_name_no_matches(self):
        # Search for something that doesn't match
        response = self.client.get('/users/', {'name': 'xyz123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_search_by_name_empty_string(self):
        # Empty search should return all users
        response = self.client.get('/users/', {'name': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)

    def test_search_by_name_partial_substring(self):
        # Search for "doe" should match "johndoe"
        response = self.client.get('/users/', {'name': 'doe'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [result['user']['username'] for result in response.data['results']]
        self.assertIn('johndoe', usernames)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_name_only_searches_username(self):
        # Search should only match username, not display_name
        response = self.client.get('/users/', {'name': 'test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [result['user']['username'] for result in response.data['results']]
        # Should only match username "testuser", not display names
        self.assertIn('testuser', usernames)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_name_combined_with_other_filters(self):
        # Combine name search with skills filter
        skill = Skill.objects.create(skill_wikidata_item="Q123456789")
        self.user1.profile.skills_known.add(skill)
        
        response = self.client.get('/users/', {'name': 'leo', 'has_skills_known': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [result['user']['username'] for result in response.data['results']]
        self.assertIn('albertoleoncio', usernames)
        # Maria should not be in results because she doesn't have skills
        self.assertNotIn('marialeonardo', usernames)
        self.assertEqual(len(response.data['results']), 1)


class SavedItemViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        CustomUser.objects.create_user(username='test2', password=str(secrets.randbits(16)))
        org = Organization.objects.create(acronym='TO', type=OrganizationType.objects.create(type_name='Type 1', type_code='TYPE1'))
        OrganizationName.objects.create(organization=org, name='Test Org', language_code='en')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_saved_items(self):
        SavedItem.objects.create(user=self.user, relation='sharer', entity='user', related_user=CustomUser.objects.get(username='test2'))
        SavedItem.objects.create(user=self.user, relation='learner', entity='org', related_org=Organization.objects.get(acronym='TO'))

        response = self.client.get('/saved_item/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        saved_items = SavedItem.objects.filter(user=self.user)
        serializer = SavedItemSerializer(saved_items, many=True)
        self.assertEqual(response.data['results'], serializer.data)

    def test_retrieve_saved_item(self):
        saved_item = SavedItem.objects.create(user=self.user, relation='sharer', entity='user', related_user=CustomUser.objects.get(username='test2'))

        response = self.client.get(f'/saved_item/{saved_item.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = SavedItemSerializer(saved_item)
        self.assertEqual(response.data, serializer.data)

    def test_create_saved_item(self):
        data = {'relation': 'sharer', 'entity': 'user', 'entity_id': CustomUser.objects.get(username='test2').pk}
        response = self.client.post('/saved_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        saved_item = SavedItem.objects.get(user=self.user, relation='sharer', entity='user', related_user=CustomUser.objects.get(username='test2'))
        self.assertIsNotNone(saved_item)

        data = {'relation': 'learner', 'entity': 'org', 'entity_id': Organization.objects.get(acronym='TO').pk}
        response = self.client.post('/saved_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        saved_item = SavedItem.objects.get(user=self.user, relation='learner', entity='org', related_org=Organization.objects.get(acronym='TO'))
        self.assertIsNotNone(saved_item)

    def test_create_saved_item_not_existing_entity(self):
        data = {'relation': 'sharer', 'entity': 'user', 'entity_id': 999}
        response = self.client.post('/saved_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {'relation': 'sharer', 'entity': 'org', 'entity_id': 999}
        response = self.client.post('/saved_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_saved_item_already_exists(self):
        SavedItem.objects.create(user=self.user, relation='sharer', entity='user', related_user=CustomUser.objects.get(username='test2'))
        data = {'relation': 'sharer', 'entity': 'user', 'entity_id': CustomUser.objects.get(username='test2').pk}
        response = self.client.post('/saved_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_208_ALREADY_REPORTED)

    def test_create_saved_item_invalid_entity(self):
        data = {'relation': 'sharer', 'entity': 'invalid', 'entity_id': 1}
        response = self.client.post('/saved_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Invalid entity type.')

    def test_delete_saved_item(self):
        saved_item = SavedItem.objects.create(user=self.user, relation='sharer', entity='user', related_user=CustomUser.objects.get(username='test2'))

        response = self.client.delete(f'/saved_item/{saved_item.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(SavedItem.DoesNotExist):
            SavedItem.objects.get(pk=saved_item.pk)

    def test_update_saved_item(self):
        saved_item = SavedItem.objects.create(user=self.user, relation='sharer', entity='user', related_user=CustomUser.objects.get(username='test2'))
        data = {'relation': 'learner', 'entity': 'org', 'entity_id': Organization.objects.get(acronym='TO').pk}

        response = self.client.put(f'/saved_item/{saved_item.pk}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data['message'], 'Updates are not allowed for saved items.')

    def test_partial_update_saved_item_not_allowed(self):
        saved_item = SavedItem.objects.create(user=self.user, relation='sharer', entity='user', related_user=CustomUser.objects.get(username='test2'))
        data = {'entity': 'org'}

        response = self.client.patch(f'/saved_item/{saved_item.pk}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data['message'], 'Partial updates are not allowed for saved items.')

    def test_list_saved_items_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/saved_item/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_saved_item_unauthenticated(self):
        self.client.force_authenticate(user=None)
        data = {'item_type': 'type1', 'item_id': 1}
        response = self.client.post('/saved_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BadgeViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.badge = Badge.objects.create(name='Test Badge', picture='test.png', description='Test Description')

    def test_list_badges(self):
        response = self.client.get('/badges/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        badges = Badge.objects.all()
        serializer = BadgeSerializer(badges, many=True)
        self.assertEqual(response.data['results'], serializer.data)

    def test_retrieve_badge(self):
        response = self.client.get(f'/badges/{self.badge.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = BadgeSerializer(self.badge)
        self.assertEqual(response.data, serializer.data)


class UserBadgeViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.badge = Badge.objects.create(name='Test Badge', picture='test.png', description='Test Description')
        self.user_badge = UserBadge.objects.create(user=self.user, badge=self.badge, is_displayed=True)

    def test_list_user_badges(self):
        response = self.client.get('/user_badge/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user_badges = UserBadge.objects.filter(user=self.user)
        serializer = UserBadgeSerializer(user_badges, many=True)
        self.assertEqual(response.data['results'], serializer.data)

    def test_retrieve_user_badge(self):
        response = self.client.get(f'/user_badge/{self.user_badge.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = UserBadgeSerializer(self.user_badge)
        self.assertEqual(response.data, serializer.data)

    def test_create_user_badge(self):
        data = {
            'user': self.user.pk,
            'badge': self.badge.pk,
        }
        response = self.client.post('/user_badge/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_badge(self):
        url = f'/user_badge/{self.user_badge.pk}/'
        updated_data = {
            'is_displayed': False
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user_badge.refresh_from_db()
        self.assertEqual(self.user_badge.is_displayed, updated_data['is_displayed'])

    def test_update_user_badge_no_permission(self):
        other_user = CustomUser.objects.create_user(username='other_user', password=str(secrets.randbits(16)))
        other_user_badge = UserBadge.objects.create(user=other_user, badge=self.badge, is_displayed=True)

        url = f'/user_badge/{other_user_badge.pk}/'
        updated_data = {
            'is_displayed': False
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_user_badge(self):
        response = self.client.delete(f'/user_badge/{self.user_badge.pk}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_partial_update_user_badge(self):
        url = f'/user_badge/{self.user_badge.pk}/'
        updated_data = {
            'is_displayed': False
        }
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

class StatisticsViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client.force_authenticate(self.user)

    def test_statistics_view_empty(self):
        response = self.client.get('/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [
            "total_users", "new_users", "active_users", "total_capacities", "new_capacities",
            "total_messages", "new_messages", "total_organizations", "new_organizations"
        ]
        for key in expected_keys:
            self.assertIn(key, response.data)
            self.assertIsInstance(response.data[key], int)

    def test_statistics_view_counts(self):
        # Create a skill with creation date this month
        Skill.objects.create(skill_wikidata_item="Q1")

        # Create a message with date this month
        Message.objects.create(sender=self.user, receiver=self.user, method="email", status="sent")

        # Create an organization with managers and management joined this month
        org_type = OrganizationType.objects.create(type_name='Type', type_code='T')
        org = Organization.objects.create(acronym='O', type=org_type)
        OrganizationName.objects.create(organization=org, name='Org', language_code='en')
        org.managers.add(self.user)
        org.save()

        response = self.client.get('/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['total_users'], 1)
        self.assertGreaterEqual(response.data['total_capacities'], 1)
        self.assertGreaterEqual(response.data['total_messages'], 1)
        self.assertGreaterEqual(response.data['total_organizations'], 1)


class RecommendationViewTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.profile = Profile.objects.get(user=self.user)
        
        # Create skills
        self.skill1 = Skill.objects.create(skill_wikidata_item='Q28865')
        self.skill2 = Skill.objects.create(skill_wikidata_item='Q186135')
        self.skill3 = Skill.objects.create(skill_wikidata_item='Q2005')
        
        # Set up user profile with skills
        self.profile.skills_known.add(self.skill1)
        self.profile.skills_available.add(self.skill1)
        self.profile.skills_wanted.add(self.skill2)
        
    def test_recommendation_endpoint_authenticated(self):
        response = self.client.get('/recommendation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('share_with', response.data)
        self.assertIn('learn_from', response.data)
        self.assertIn('same_language', response.data)
        self.assertIn('share_with_orgs', response.data)
        self.assertIn('learn_from_orgs', response.data)
        self.assertIn('new_skills', response.data)
        self.assertIn('events', response.data)

    def test_recommendation_endpoint_unauthenticated(self):
        client = APIClient()
        response = client.get('/recommendation/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_recommendation_share_with_orgs(self):
        # Create an organization that wants a skill the user can teach
        org_type = OrganizationType.objects.create(type_code='UG', type_name='User Group')
        org = Organization.objects.create(
            acronym='TO',
            type=org_type
        )
        OrganizationName.objects.create(organization=org, name='Test Organization', language_code='en')
        org.managers.add(self.user)
        org.wanted_capacities.add(self.skill1)  # Org wants what user can teach
        
        response = self.client.get('/recommendation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['share_with_orgs']), 1)
        self.assertEqual(response.data['share_with_orgs'][0]['id'], org.id)
        self.assertEqual(response.data['share_with_orgs'][0]['display_name'], 'Test Organization')
        self.assertEqual(response.data['share_with_orgs'][0]['matches'], 1)

    def test_recommendation_learn_from_orgs(self):
        # Create an organization that can teach a skill the user wants
        org_type = OrganizationType.objects.create(type_code='UG', type_name='User Group')
        org = Organization.objects.create(
            acronym='TEACH',
            type=org_type
        )
        OrganizationName.objects.create(organization=org, name='Teaching Organization', language_code='en') 
        org.managers.add(self.user)
        org.available_capacities.add(self.skill2)  # Org can teach what user wants
        
        response = self.client.get('/recommendation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['learn_from_orgs']), 1)
        self.assertEqual(response.data['learn_from_orgs'][0]['id'], org.id)
        self.assertEqual(response.data['learn_from_orgs'][0]['display_name'], 'Teaching Organization')
        self.assertEqual(response.data['learn_from_orgs'][0]['matches'], 1)

    def test_recommendation_orgs_without_managers_excluded(self):
        # Create an organization without managers (should be excluded)
        org_type = OrganizationType.objects.create(type_code='UG', type_name='User Group')
        org = Organization.objects.create(
            acronym='NM',
            type=org_type
        )
        OrganizationName.objects.create(organization=org, name='No Manager Org', language_code='en')
        org.wanted_capacities.add(self.skill1)
        
        response = self.client.get('/recommendation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['share_with_orgs']), 0)

    def test_recommendation_limit_parameter(self):
        # Create multiple organizations
        org_type = OrganizationType.objects.create(type_code='UG', type_name='User Group')
        for i in range(15):
            org = Organization.objects.create(
                acronym=f'TO{i}',
                type=org_type
            )
            OrganizationName.objects.create(organization=org, name=f'Test Org {i}', language_code='en')
            org.managers.add(self.user)
            org.wanted_capacities.add(self.skill1)
        
        # Test with limit=5
        response = self.client.get('/recommendation/?limit=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['share_with_orgs']), 5)

    def test_recommendation_multiple_skill_matches(self):
        # Create an organization that matches multiple skills
        org_type = OrganizationType.objects.create(type_code='UG', type_name='User Group')
        org = Organization.objects.create(
            acronym='MSO',
            type=org_type
        )
        OrganizationName.objects.create(organization=org, name='Multi-skill Org', language_code='en')
        org.managers.add(self.user)
        
        # Add more skills to user
        self.profile.skills_available.add(self.skill2, self.skill3)
        
        # Org wants multiple skills the user can teach
        org.wanted_capacities.add(self.skill1, self.skill2, self.skill3)
        
        response = self.client.get('/recommendation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['share_with_orgs']), 1)
        # Should match 3 skills: skill1, skill2, skill3
        self.assertEqual(response.data['share_with_orgs'][0]['matches'], 3)
        

class UsersOrderingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create multiple users with different attributes
        self.user1 = CustomUser.objects.create_user(username='alpha_user', password=str(secrets.randbits(16)))
        self.user2 = CustomUser.objects.create_user(username='beta_user', password=str(secrets.randbits(16)))
        self.user3 = CustomUser.objects.create_user(username='gamma_user', password=str(secrets.randbits(16)))

    def test_users_ordering_by_last_update_desc(self):
        # Since last_update has auto_now=True, we need to update the profile to trigger a new timestamp
        # The last user to be saved will have the most recent last_update
        self.user3.profile.about = 'Updated bio for user3'
        self.user3.profile.save()

        response = self.client.get('/users/?ordering=-last_update')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertGreaterEqual(len(results), 3)
        # user3 should be first as it was updated most recently
        self.assertEqual(results[0]['user']['username'], 'gamma_user')


class LanguagesByTerritoryViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = CustomUser.objects.create_user(username='user1', password=str(secrets.randbits(16)))
        self.user2 = CustomUser.objects.create_user(username='user2', password=str(secrets.randbits(16)))
        self.user3 = CustomUser.objects.create_user(username='user3', password=str(secrets.randbits(16)))

        # Create territories
        self.territory1 = Territory.objects.create(territory_name='Territory 1')
        self.territory2 = Territory.objects.create(territory_name='Territory 2')

        # Create languages
        self.lang_en = Language.objects.create(language_name='English', language_code='en')
        self.lang_es = Language.objects.create(language_name='Spanish', language_code='es')
        self.lang_fr = Language.objects.create(language_name='French', language_code='fr')

    def test_languages_by_territory_empty(self):
        """Test endpoint with no language/territory data"""
        response = self.client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})

    def test_languages_by_territory_no_auth_required(self):
        """Test that endpoint works without authentication"""
        client = APIClient()  # No auth
        response = client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_languages_by_territory_basic(self):
        """Test basic language aggregation by territory"""
        # User1 in Territory1, speaks English
        self.user1.profile.territory.set([self.territory1])
        LanguageProficiency.objects.create(
            profile=self.user1.profile,
            language=self.lang_en,
            proficiency='3'
        )

        response = self.client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check structure
        self.assertIn(str(self.territory1.id), response.data)
        self.assertIn(str(self.lang_en.id), response.data[str(self.territory1.id)])
        self.assertEqual(response.data[str(self.territory1.id)][str(self.lang_en.id)], 1)

    def test_languages_by_territory_multiple_users_same_territory(self):
        """Test aggregation when multiple users in same territory speak same language"""
        # Both users in Territory1, both speak English
        self.user1.profile.territory.set([self.territory1])
        self.user2.profile.territory.set([self.territory1])

        LanguageProficiency.objects.create(
            profile=self.user1.profile,
            language=self.lang_en,
            proficiency='3'
        )
        LanguageProficiency.objects.create(
            profile=self.user2.profile,
            language=self.lang_en,
            proficiency='4'
        )

        response = self.client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should count 2 users for English in Territory1
        self.assertEqual(response.data[str(self.territory1.id)][str(self.lang_en.id)], 2)

    def test_languages_by_territory_excludes_zero_proficiency(self):
        """Test that proficiency=0 languages are excluded"""
        self.user1.profile.territory.set([self.territory1])

        # English with proficiency 3 (should be counted)
        LanguageProficiency.objects.create(
            profile=self.user1.profile,
            language=self.lang_en,
            proficiency='3'
        )
        # Spanish with proficiency 0 (should NOT be counted)
        LanguageProficiency.objects.create(
            profile=self.user1.profile,
            language=self.lang_es,
            proficiency='0'
        )

        response = self.client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        territory_data = response.data[str(self.territory1.id)]
        self.assertIn(str(self.lang_en.id), territory_data)
        self.assertNotIn(str(self.lang_es.id), territory_data)

    def test_languages_by_territory_multiple_territories(self):
        """Test aggregation across multiple territories"""
        # User1 in Territory1, speaks English
        self.user1.profile.territory.set([self.territory1])
        LanguageProficiency.objects.create(
            profile=self.user1.profile,
            language=self.lang_en,
            proficiency='3'
        )

        # User2 in Territory2, speaks Spanish
        self.user2.profile.territory.set([self.territory2])
        LanguageProficiency.objects.create(
            profile=self.user2.profile,
            language=self.lang_es,
            proficiency='4'
        )

        response = self.client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Territory1 should have English
        self.assertIn(str(self.territory1.id), response.data)
        self.assertEqual(response.data[str(self.territory1.id)][str(self.lang_en.id)], 1)

        # Territory2 should have Spanish
        self.assertIn(str(self.territory2.id), response.data)
        self.assertEqual(response.data[str(self.territory2.id)][str(self.lang_es.id)], 1)

    def test_languages_by_territory_user_in_multiple_territories(self):
        """Test when a user belongs to multiple territories"""
        # User1 in both territories, speaks English
        self.user1.profile.territory.set([self.territory1, self.territory2])
        LanguageProficiency.objects.create(
            profile=self.user1.profile,
            language=self.lang_en,
            proficiency='3'
        )

        response = self.client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Both territories should have English counted
        self.assertEqual(response.data[str(self.territory1.id)][str(self.lang_en.id)], 1)
        self.assertEqual(response.data[str(self.territory2.id)][str(self.lang_en.id)], 1)

    def test_languages_by_territory_excludes_inactive_users(self):
        """Test that inactive users are excluded"""
        self.user1.profile.territory.set([self.territory1])
        LanguageProficiency.objects.create(
            profile=self.user1.profile,
            language=self.lang_en,
            proficiency='3'
        )

        # Deactivate user1
        self.user1.is_active = False
        self.user1.save()

        response = self.client.get('/statistics/languages-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Territory1 should not appear since only user was inactive
        self.assertNotIn(str(self.territory1.id), response.data)


class CapacitiesByTerritoryViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = CustomUser.objects.create_user(username='user1', password=str(secrets.randbits(16)))
        self.user2 = CustomUser.objects.create_user(username='user2', password=str(secrets.randbits(16)))

        # Create territories
        self.territory1 = Territory.objects.create(territory_name='Territory 1')
        self.territory2 = Territory.objects.create(territory_name='Territory 2')

        # Create skills/capacities
        self.skill1 = Skill.objects.create(skill_wikidata_item='Q123')
        self.skill2 = Skill.objects.create(skill_wikidata_item='Q456')

    def test_capacities_by_territory_empty(self):
        """Test endpoint with no capacity/territory data"""
        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})

    def test_capacities_by_territory_no_auth_required(self):
        """Test that endpoint works without authentication"""
        client = APIClient()  # No auth
        response = client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_capacities_by_territory_available_skills(self):
        """Test aggregation of available skills by territory"""
        self.user1.profile.territory.set([self.territory1])
        self.user1.profile.skills_known.add(self.skill1)
        self.user1.profile.skills_available.add(self.skill1)

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        territory_data = response.data[str(self.territory1.id)]
        skill_data = territory_data[str(self.skill1.id)]

        self.assertEqual(skill_data['available'], 1)
        self.assertEqual(skill_data['wanted'], 0)

    def test_capacities_by_territory_wanted_skills(self):
        """Test aggregation of wanted skills by territory"""
        self.user1.profile.territory.set([self.territory1])
        self.user1.profile.skills_wanted.add(self.skill1)

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        territory_data = response.data[str(self.territory1.id)]
        skill_data = territory_data[str(self.skill1.id)]

        self.assertEqual(skill_data['available'], 0)
        self.assertEqual(skill_data['wanted'], 1)

    def test_capacities_by_territory_both_available_and_wanted(self):
        """Test when different users have same skill available and wanted"""
        # User1 has skill1 available
        self.user1.profile.territory.set([self.territory1])
        self.user1.profile.skills_known.add(self.skill1)
        self.user1.profile.skills_available.add(self.skill1)

        # User2 wants skill1
        self.user2.profile.territory.set([self.territory1])
        self.user2.profile.skills_wanted.add(self.skill1)

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        territory_data = response.data[str(self.territory1.id)]
        skill_data = territory_data[str(self.skill1.id)]

        self.assertEqual(skill_data['available'], 1)
        self.assertEqual(skill_data['wanted'], 1)

    def test_capacities_by_territory_multiple_users_same_skill(self):
        """Test aggregation when multiple users have same skill available"""
        self.user1.profile.territory.set([self.territory1])
        self.user1.profile.skills_known.add(self.skill1)
        self.user1.profile.skills_available.add(self.skill1)

        self.user2.profile.territory.set([self.territory1])
        self.user2.profile.skills_known.add(self.skill1)
        self.user2.profile.skills_available.add(self.skill1)

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        territory_data = response.data[str(self.territory1.id)]
        skill_data = territory_data[str(self.skill1.id)]

        self.assertEqual(skill_data['available'], 2)

    def test_capacities_by_territory_multiple_territories(self):
        """Test aggregation across multiple territories"""
        # User1 in Territory1 with skill1 available
        self.user1.profile.territory.set([self.territory1])
        self.user1.profile.skills_known.add(self.skill1)
        self.user1.profile.skills_available.add(self.skill1)

        # User2 in Territory2 with skill2 wanted
        self.user2.profile.territory.set([self.territory2])
        self.user2.profile.skills_wanted.add(self.skill2)

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Territory1 should have skill1 available
        self.assertEqual(response.data[str(self.territory1.id)][str(self.skill1.id)]['available'], 1)

        # Territory2 should have skill2 wanted
        self.assertEqual(response.data[str(self.territory2.id)][str(self.skill2.id)]['wanted'], 1)

    def test_capacities_by_territory_user_in_multiple_territories(self):
        """Test when a user belongs to multiple territories"""
        self.user1.profile.territory.set([self.territory1, self.territory2])
        self.user1.profile.skills_known.add(self.skill1)
        self.user1.profile.skills_available.add(self.skill1)

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Both territories should have skill1 available
        self.assertEqual(response.data[str(self.territory1.id)][str(self.skill1.id)]['available'], 1)
        self.assertEqual(response.data[str(self.territory2.id)][str(self.skill1.id)]['available'], 1)

    def test_capacities_by_territory_excludes_inactive_users(self):
        """Test that inactive users are excluded"""
        self.user1.profile.territory.set([self.territory1])
        self.user1.profile.skills_known.add(self.skill1)
        self.user1.profile.skills_available.add(self.skill1)

        # Deactivate user1
        self.user1.is_active = False
        self.user1.save()

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Territory1 should not appear since only user was inactive
        self.assertNotIn(str(self.territory1.id), response.data)

    def test_capacities_by_territory_multiple_skills_per_user(self):
        """Test when a user has multiple skills"""
        self.user1.profile.territory.set([self.territory1])
        self.user1.profile.skills_known.add(self.skill1, self.skill2)
        self.user1.profile.skills_available.add(self.skill1)
        self.user1.profile.skills_wanted.add(self.skill2)

        response = self.client.get('/statistics/capacities-by-territory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        territory_data = response.data[str(self.territory1.id)]

        # skill1 should be available
        self.assertEqual(territory_data[str(self.skill1.id)]['available'], 1)
        self.assertEqual(territory_data[str(self.skill1.id)]['wanted'], 0)

        # skill2 should be wanted
        self.assertEqual(territory_data[str(self.skill2.id)]['available'], 0)
        self.assertEqual(territory_data[str(self.skill2.id)]['wanted'], 1)
