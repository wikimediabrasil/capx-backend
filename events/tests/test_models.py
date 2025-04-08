from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from events.models import Events
from users.models import CustomUser
from orgs.models import Organization, OrganizationType
from skills.models import Skill
import secrets


class EventsModelTest(TestCase):
    
    def setUp(self):
        # Create a user
        self.test_user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.test_user.save()
        
        self.organization_type = OrganizationType.objects.create(type_name='Type 1', type_code='TYPE1')
        self.organization = Organization.objects.create(
            display_name='New Organization',
            acronym='NO',
            type=self.organization_type,
        )

    def test_event_creation(self):
        # Create an event
        Events.objects.create(
            name='Sample Event',
            type_of_location='virtual',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            organization=self.organization,
            creator=self.test_user,
        )

        # Get the event
        event = Events.objects.get(name='Sample Event')
        expected_name = f'{event.name}'
        expected_type_of_location = f'{event.type_of_location}'
        expected_time_begin = f'{event.time_begin}'
        expected_time_end = f'{event.time_end}'

        self.assertEqual(str(event), 'Sample Event')
        self.assertEqual(expected_name, 'Sample Event')
        self.assertEqual(expected_type_of_location, 'virtual')
        self.assertEqual(expected_time_begin, '2021-10-10 10:00:00+00:00')
        self.assertEqual(expected_time_end, '2021-10-10 12:00:00+00:00')
