import secrets
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from orgs.models import OrganizationType, Organization, TagDiff, Document
from users.models import CustomUser
from users.submodels import Territory
from skills.models import Skill
from django.db import models
from events.models import Events


class OrganizationViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.organization_type = OrganizationType.objects.create(type_name='Type 1', type_code='TYPE1')
        self.territory = Territory.objects.create(territory_name='Territory 1')
    
    def test_get_orgs_list_unauthenticated(self):
        response = self.client.get('/organizations/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_org_unauthenticated(self):
        org_data = {
            'display_name': 'New Organization',
            'acronym': 'NO',
            'type': self.organization_type.pk,
            'territory': self.territory.pk,
        }

        response = self.client.post('/organizations/', org_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_org_authenticated(self):
        org_data = {
            'display_name': 'New Organization',
            'acronym': 'NO',
            'type': self.organization_type.pk,
            'territory': self.territory.pk,
        }

        self.client.force_authenticate(self.user)
        response = self.client.post('/organizations/', org_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_org_staff(self):
        org_data = {
            'display_name': 'New Organization',
            'acronym': 'NO',
            'type': self.organization_type.pk,
            'territory': self.territory.pk,
        }

        self.user.is_staff = True
        self.client.force_authenticate(self.user)
        response = self.client.post('/organizations/', org_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_org_event(self):
        self.user.is_staff = True
        self.client.force_authenticate(self.user)

        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        event = Events.objects.create(
            name='Test Event', 
            organization=organization,
            time_begin='2023-01-01T00:00:00Z',
            time_end='2023-01-02T00:00:00Z',
        )
        new_data = {
            'display_name': 'New Organization',
            'acronym': 'UO',
            'choose_events': [event.pk],
        }
        response = self.client.post('/organizations/', new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        new_data = {
            'display_name': 'New Organization',
            'acronym': 'UO',
            'choose_events': [],
        }
        response = self.client.post('/organizations/', new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_list_orgs_authenticated(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        organization.territory.set([self.territory])
        response = self.client.get('/organizations/')
        self.assertEqual(len(response.data['results']), 0)

        Organization.objects.create(
            display_name='New Organization 2',
            acronym='NO2', 
            type=self.organization_type,
        )
        organization.territory.set([self.territory])    
        organization.managers.set([self.user])
        response = self.client.get('/organizations/')
        self.assertEqual(len(response.data['results']), 1)


    def test_list_orgs_staff(self):
        self.user.is_staff = True
        self.client.force_authenticate(self.user)
        response = self.client.get('/organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

        org_data = {
            'display_name': 'New Organization',
            'acronym': 'NO',
            'type': self.organization_type.pk,
            'territory': self.territory.pk,
        }
        self.client.post('/organizations/', org_data)
        response = self.client.get('/organizations/')
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_org(self):
        self.client.force_authenticate(self.user)

        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        organization.territory.set([self.territory])
        response = self.client.get(f'/organizations/{organization.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.user.is_staff = True
        self.user.save()
        response = self.client.get(f'/organizations/{organization.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.is_staff = False
        self.user.save()
        organization.managers.set([self.user])
        response = self.client.get(f'/organizations/{organization.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_org_multiple_managers(self):
        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        organization.territory.set([self.territory])
        manager = CustomUser.objects.create_user(username='manager', password=str(secrets.randbits(16)))
        organization.managers.set([self.user, manager])

        self.client.force_authenticate(self.user)
        response = self.client.get(f'/organizations/{organization.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_org(self):
        self.client.force_authenticate(self.user)

        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        manager = CustomUser.objects.create_user(username='manager', password=str(secrets.randbits(16)))
        organization.managers.set([manager])
        organization.territory.set([self.territory])
        response = self.client.put(f'/organizations/{organization.pk}/', {'display_name': 'New Name','acronym': 'NN'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.user.is_staff = True
        response = self.client.put(f'/organizations/{organization.pk}/', {'display_name': 'New Name','acronym': 'NN'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.is_staff = False
        organization.managers.set([self.user])
        response = self.client.put(f'/organizations/{organization.pk}/', {'display_name': 'Other New Name','acronym': 'ONN'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_org_event(self):
        self.user.is_staff = True
        self.client.force_authenticate(self.user)

        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        organization2 = Organization.objects.create(
            display_name='New Organization 2',
            acronym='NO2',
            type=self.organization_type,
        )
        event = Events.objects.create(
            name='Test Event', 
            organization=organization2,
            time_begin='2023-01-01T00:00:00Z',
            time_end='2023-01-02T00:00:00Z',
        )
        updated_data = {
            'display_name': 'Updated Organization',
            'acronym': 'UO',
            'choose_events': [event.pk],
        }
        response = self.client.put(f'/organizations/{organization.pk}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        event.organization = organization
        event.save()
        response = self.client.put(f'/organizations/{organization.pk}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_partial_update_org(self):
        self.client.force_authenticate(self.user)

        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        organization.territory.set([self.territory])
        response = self.client.patch(f'/organizations/{organization.pk}/', {'display_name': 'New Name'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        self.user.is_staff = True
        response = self.client.patch(f'/organizations/{organization.pk}/', {'display_name': 'New Name'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        self.user.is_staff = False
        organization.managers.set([self.user])
        response = self.client.patch(f'/organizations/{organization.pk}/', {'display_name': 'Other New Name'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_org(self):
        self.client.force_authenticate(self.user)

        organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )
        manager = CustomUser.objects.create_user(username='manager', password=str(secrets.randbits(16)))
        organization.managers.set([manager])
        organization.territory.set([self.territory])
        response = self.client.delete(f'/organizations/{organization.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.user.is_staff = True
        response = self.client.delete(f'/organizations/{organization.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_tagdiffs(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/tag_diff/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        TagDiff.objects.create(tag='Tag 1')
        response = self.client.get('/tag_diff/')
        self.assertEqual(len(response.data['results']), 1)

    def test_create_tagdiff(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/tag_diff/', {'tag': 'Tag 1'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.user.is_staff = True
        response = self.client.post('/tag_diff/', {'tag': 'Tag 1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_tagdiff(self):
        self.client.force_authenticate(self.user)
        tagdiff = TagDiff.objects.create(tag='Tag 1')
        response = self.client.get(f'/tag_diff/{tagdiff.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_tagdiff(self):
        self.client.force_authenticate(self.user)
        TagDiff.objects.create(tag='Tag 1')
        response = self.client.put('/tag_diff/1/', {'tag': 'Tag 2'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_tagdiff(self):
        self.client.force_authenticate(self.user)
        TagDiff.objects.create(tag='Tag 1')
        response = self.client.patch('/tag_diff/1/', {'tag': 'Tag 2'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_documents(self):
        self.client.force_authenticate(self.user)
        Document.objects.create(url='https://commons.wikimedia.org/wiki/File:filename.ext')
        response = self.client.put('/document/1/', {'url': 'https://commons.wikimedia.org/wiki/File:filename2.ext'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_documents(self):
        self.client.force_authenticate(self.user)
        Document.objects.create(url='https://commons.wikimedia.org/wiki/File:filename.ext')
        response = self.client.patch('/document/1/', {'url': 'https://commons.wikimedia.org/wiki/File:filename2.ext'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

class OrganizationFilterViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.staff_user = CustomUser.objects.create_user(username='staff', password=str(secrets.randbits(16)), is_staff=True)
        self.client = APIClient()
        self.organization = Organization.objects.create(display_name='Test Organization', acronym='TO')
        self.organization.managers.add(self.user)

    def test_get_queryset_as_staff(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get('/organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.count())

    def test_get_queryset_as_non_staff(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(managers__isnull=False).distinct().count())

    def test_get_queryset_by_territory(self):
        self.territory = Territory.objects.create(territory_name='Territory 1')
        self.child_territory = Territory.objects.create(territory_name='Child Territory 1')
        self.child_territory.parent_territory.set([self.territory])
        self.organization.territory.set([self.child_territory])

        self.client.force_authenticate(self.staff_user)
        response = self.client.get('/organizations/', {'territory': self.territory.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_queryset_has_capacities_known_true(self):
        self.client.force_authenticate(self.staff_user)
        self.organization.known_capacities.add(Skill.objects.create(skill_wikidata_item="Q123456789"))
        response = self.client.get('/organizations/', {'has_capacities_known': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(known_capacities__isnull=False).distinct().count())

    def test_get_queryset_has_capacities_known_false(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get('/organizations/', {'has_capacities_known': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(known_capacities__isnull=True).distinct().count())

    def test_get_queryset_has_capacities_available_true(self):
        self.client.force_authenticate(self.staff_user)
        self.organization.available_capacities.add(Skill.objects.create(skill_wikidata_item="Q123456789"))
        response = self.client.get('/organizations/', {'has_capacities_available': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(available_capacities__isnull=False).distinct().count())

    def test_get_queryset_has_capacities_available_false(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get('/organizations/', {'has_capacities_available': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(available_capacities__isnull=True).distinct().count())

    def test_get_queryset_has_capacities_wanted_true(self):
        self.client.force_authenticate(self.staff_user)
        self.organization.wanted_capacities.add(Skill.objects.create(skill_wikidata_item="Q123456789"))
        response = self.client.get('/organizations/', {'has_capacities_wanted': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(wanted_capacities__isnull=False).distinct().count())

    def test_get_queryset_has_capacities_wanted_false(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get('/organizations/', {'has_capacities_wanted': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(wanted_capacities__isnull=True).distinct().count())

    def test_get_queryset_has_any_capacities_true(self):
        self.client.force_authenticate(self.staff_user)
        self.organization.known_capacities.add(Skill.objects.create(skill_wikidata_item="Q123456789"))
        response = self.client.get('/organizations/', {'has_any_capacities': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(
            models.Q(known_capacities__isnull=False) |
            models.Q(available_capacities__isnull=False) |
            models.Q(wanted_capacities__isnull=False)
        ).distinct().count())

    def test_get_queryset_has_any_capacities_false(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get('/organizations/', {'has_any_capacities': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Organization.objects.filter(
            models.Q(known_capacities__isnull=True) &
            models.Q(available_capacities__isnull=True) &
            models.Q(wanted_capacities__isnull=True)
        ).distinct().count())