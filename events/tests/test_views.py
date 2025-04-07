from django.test import TestCase
from users.models import CustomUser
from orgs.models import Organization
from events.models import Events
from rest_framework.test import APIClient
from rest_framework import status
import secrets

class EventViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.organization = Organization.objects.create(display_name='Test Org')
        self.organization.managers.add(self.user)
        self.event = Events.objects.create(
            name='Test Event',
            organization=self.organization,
            type_of_location='virtual',
            time_begin='2023-10-10 10:00:00+00:00',
            time_end='2023-10-10 12:00:00+00:00'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_events(self):
        response = self.client.get('/events/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_event(self):
        response = self.client.get(f'/events/{self.event.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.event.name)

    def test_create_event_as_manager(self):
        data = {
            'name': 'New Event',
            'organization': self.organization.id,
            'type_of_location': 'virtual',
            'time_begin': '2023-11-10 10:00:00+00:00',
            'time_end': '2023-11-10 12:00:00+00:00'
        }
        response = self.client.post('/events/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_event_as_non_manager(self):
        other_user = CustomUser.objects.create_user(username='test2', password=str(secrets.randbits(16)))
        self.client.force_authenticate(other_user)
        data = {
            'name': 'New Event',
            'organization': self.organization.id,
            'type_of_location': 'virtual',
            'time_begin': '2023-11-10 10:00:00+00:00',
            'time_end': '2023-11-10 12:00:00+00:00'
        }
        response = self.client.post('/events/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_event_as_manager(self):
        data = {
            'name': 'Updated Event',
            'organization': self.organization.id,
            'type_of_location': 'virtual',
            'time_begin': '2023-10-10 10:00:00+00:00',
            'time_end': '2023-10-10 12:00:00+00:00'
        }
        response = self.client.put(f'/events/{self.event.pk}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, 'Updated Event')

    def test_update_event_as_non_manager(self):
        other_user = CustomUser.objects.create_user(username='test2', password=str(secrets.randbits(16)))
        self.client.force_authenticate(other_user)
        data = {
            'name': 'Updated Event',
            'organization': self.organization.id,
            'type_of_location': 'virtual',
            'time_begin': '2023-10-10 10:00:00+00:00',
            'time_end': '2023-10-10 12:00:00+00:00'
        }
        response = self.client.put(f'/events/{self.event.pk}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_event(self):
        data = {'name': 'Partially Updated Event'}
        response = self.client.patch(f'/events/{self.event.pk}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_event_as_manager(self):
        response = self.client.delete(f'/events/{self.event.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Events.objects.filter(pk=self.event.pk).exists())

    def test_delete_event_as_non_manager(self):
        other_user = CustomUser.objects.create_user(username='test2', password=str(secrets.randbits(16)))
        self.client.force_authenticate(other_user)
        response = self.client.delete(f'/events/{self.event.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)