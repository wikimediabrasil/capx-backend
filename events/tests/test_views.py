from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from events.models import Events, EventParticipant, EventOrganizations
from events.serializers import EventParticipantSerializer
from users.models import CustomUser
from orgs.models import Organization, OrganizationType
import secrets

class EventViewSetTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username='user', password=str(secrets.randbits(16)))
        self.staff_user = CustomUser.objects.create_user(username='staff', password=str(secrets.randbits(16)), is_staff=True)
        self.regular_user = CustomUser.objects.create_user(username='regular', password=str(secrets.randbits(16)))
        self.event = Events.objects.create(
            name='Test Event',
            type_of_location='hybrid',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
        )
        self.participant = EventParticipant.objects.create(
            event=self.event, 
            participant=self.user, 
            role='organizer'
        )
        self.client.force_login(self.user)

    def test_list_events(self):
        response = self.client.get('/events/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_event(self):
        response = self.client.post('/events/', {
            'name': 'New Event',
            'type_of_location': 'hybrid',
            'time_begin': '2022-10-10 10:00:00+00:00',
            'time_end': '2022-10-10 12:00:00+00:00',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EventParticipant.objects.filter(participant=self.user, role='organizer').count(), 2)

    def test_update_event_by_organizer(self):
        response = self.client.put(f'/events/{self.event.id}/', {
            'name': 'Updated Event',
            'type_of_location': 'hybrid',
            'time_begin': '2022-10-10 10:00:00+00:00',
            'time_end': '2022-10-10 12:00:00+00:00',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_event_by_non_organizer(self):
        self.client.force_login(self.regular_user)
        response = self.client.put(f'/events/{self.event.id}/', {
            'name': 'Updated Event',
            'type_of_location': 'hybrid',
            'time_begin': '2022-10-10 10:00:00+00:00',
            'time_end': '2022-10-10 12:00:00+00:00',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_event_by_organizer(self):
        response = self.client.patch(f'/events/{self.event.id}/', {
            'name': 'Updated Event',
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_event_by_non_organizer(self):
        self.client.force_login(self.regular_user)
        response = self.client.patch(f'/events/{self.event.id}/', {
            'name': 'Updated Event',
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_event_by_admin(self):
        self.client.force_login(self.staff_user)
        response = self.client.delete(f'/events/{self.event.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_event_by_non_admin(self):
        response = self.client.delete(f'/events/{self.event.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class EventParticipantViewSetTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username='user', password=str(secrets.randbits(16)))
        self.staff_user = CustomUser.objects.create_user(username='staff', password=str(secrets.randbits(16)), is_staff=True)
        self.regular_user = CustomUser.objects.create_user(username='regular', password=str(secrets.randbits(16)))
        self.event = Events.objects.create(
            name='Test Event',
            type_of_location='hybrid',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            creator=self.user
        )
        self.participant = EventParticipant.objects.create(
            event=self.event, 
            participant=self.user, 
            role='organizer',
            confirmed_organizer=True,
            confirmed_participant=True,
        )
        self.client.force_login(self.user)

    def test_list_participants(self):
        response = self.client.get('/events_participants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(f'/events_participants/{self.participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_participant(self):
        participant = EventParticipant.objects.create(
            event=self.event,
            participant=self.regular_user,
            role='volunteer'
        )
        self.client.force_login(self.regular_user)
        response = self.client.get(f'/events_participants/{participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_organizer(self):
        response = self.client.get(f'/events_participants/{self.participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_non_participant(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(f'/events_participants/{self.participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_participant_by_organizer(self):
        new_user = CustomUser.objects.create_user(username='newuser', password=str(secrets.randbits(16)))
        response = self.client.post('/events_participants/', {'event': self.event.id, 'participant': new_user.id, 'role': 'volunteer'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_participant_by_regular(self):
        self.client.force_login(self.regular_user)
        new_user = CustomUser.objects.create_user(username='newuser', password=str(secrets.randbits(16)))
        response = self.client.post('/events_participants/', {'event': self.event.id, 'participant': new_user.id, 'role': 'volunteer'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_participant_by_staff(self):
        self.client.force_login(self.staff_user)
        new_user = CustomUser.objects.create_user(username='newuser', password=str(secrets.randbits(16)))
        response = self.client.post('/events_participants/', {'event': self.event.id, 'participant': new_user.id, 'role': 'volunteer'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_participant_by_organizer(self):
        response = self.client.put(f'/events_participants/{self.participant.id}/', {
            'event': self.event.id,
            'participant': self.participant.id,
            'role': 'committee'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_participant_by_regular(self):
        self.client.force_login(self.regular_user)
        response = self.client.put(f'/events_participants/{self.participant.id}/', {
            'event': self.event.id,
            'participant': self.participant.id,
            'role': 'committee'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_participant_by_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.put(f'/events_participants/{self.participant.id}/', {
            'event': self.event.id,
            'participant': self.participant.id,
            'role': 'committee'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_unconfirm_creator_by_committee(self):
        EventParticipant.objects.create(
            event=self.event,
            participant=self.regular_user,
            role='committee'
        )
        self.client.force_login(self.regular_user)

        self.assertTrue(EventParticipant.objects.get(event=self.event, participant=self.participant.participant).confirmed_organizer)
        self.assertTrue(self.event.creator == self.participant.participant)

        response = self.client.put(f'/events_participants/{self.participant.id}/', {
            'event': self.event.id,
            'participant': self.participant.id,
            'role': 'organizer',
            'confirmed_organizer': False
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_unconfirm_participant_by_committee(self):
        participant = EventParticipant.objects.create(
            event=self.event,
            participant=self.regular_user,
            role='volunteer',
            confirmed_participant=True
        )
        response = self.client.put(f'/events_participants/{participant.id}/', {
            'event': self.event.id,
            'participant': participant.id,
            'role': 'volunteer',
            'confirmed_participant': False
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_participant_by_organizer(self):
        response = self.client.delete(f'/events_participants/{self.participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_participant_by_regular(self):
        self.client.force_login(self.regular_user)
        response = self.client.delete(f'/events_participants/{self.participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_participant_by_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.delete(f'/events_participants/{self.participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_partial_update(self):
        self.client.force_login(self.staff_user)
        response = self.client.patch(f'/events_participants/{self.participant.id}/', {'role': 'committee'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class EventOrganizationsViewSetTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username='user', password=str(secrets.randbits(16)))
        self.staff_user = CustomUser.objects.create_user(username='staff', password=str(secrets.randbits(16)), is_staff=True)
        self.regular_user = CustomUser.objects.create_user(username='regular', password=str(secrets.randbits(16)))
        self.manager_user = CustomUser.objects.create_user(username='manager', password=str(secrets.randbits(16)))
        self.event = Events.objects.create(
            name='Test Event',
            type_of_location='hybrid',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            creator=self.user
        )
        EventParticipant.objects.create(
            event=self.event, 
            participant=self.user, 
            role='organizer'
        )
        org_type =  OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )
        self.organization = Organization.objects.create(
            display_name='Sample Organization',
            acronym='SO',
            type=org_type,
        )
        self.event_organization = EventOrganizations.objects.create(
            event=self.event, 
            organization=self.organization, 
            role='sponsor',
            confirmed_organizer=False,
            confirmed_organization=False,
        )
        self.organization.managers.add(self.manager_user)
        self.client.force_login(self.user)
    
    def test_list_organizations(self):
        response = self.client.get('/events_organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(f'/events_organizations/{self.event_organization.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_organization_manager(self):
        self.client.force_login(self.manager_user)
        response = self.client.get(f'/events_organizations/{self.event_organization.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_as_creator(self):
        response = self.client.get(f'/events_organizations/{self.event_organization.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_organization_by_organizer(self):
        response = self.client.post('/events_organizations/', {'event': self.event.id, 'organization': self.organization.pk, 'role': 'sponsor'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_organization_by_regular(self):
        self.client.force_login(self.regular_user)
        response = self.client.post('/events_organizations/', {'event': self.event.id, 'organization': self.organization.pk, 'role': 'sponsor'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_organization_by_creator(self):
        response = self.client.put(f'/events_organizations/{self.event_organization.id}/', {'event': self.event.id, 'organization': self.organization.pk, 'confirmed_organizer': True, 'role': 'sponsor'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_organization_by_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.put(f'/events_organizations/{self.event_organization.id}/', {'event': self.event.id, 'organization': self.organization.pk, 'role': 'supporter'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_organization_by_regular(self):
        self.client.force_login(self.regular_user)
        response = self.client.put(f'/events_organizations/{self.event_organization.id}/', {'event': self.event.id, 'organization': self.organization.pk, 'role': 'supporter'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_organization_by_admin(self):
        self.client.force_login(self.staff_user)
        response = self.client.delete(f'/events_organizations/{self.event_organization.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_organization_by_creator(self):
        response = self.client.delete(f'/events_organizations/{self.event_organization.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_organization_by_manager(self):
        self.client.force_login(self.manager_user)
        response = self.client.delete(f'/events_organizations/{self.event_organization.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_organization_by_regular(self):
        self.client.force_login(self.regular_user)
        response = self.client.delete(f'/events_organizations/{self.event_organization.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update(self):
        response = self.client.patch(f'/events_organizations/{self.event_organization.id}/', {'role': 'supporter'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)