from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from events.models import Events
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
