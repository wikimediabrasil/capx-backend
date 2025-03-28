from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from events.models import Events, EventParticipant, EventOrganizations
from users.models import CustomUser
from orgs.models import Organization, OrganizationType
from skills.models import Skill
import secrets


class EventsModelTest(TestCase):
    
    def setUp(self):
        # Create a user
        self.test_user = CustomUser.objects.create_user(username='testuser', password=str(secrets.randbits(16)))
        self.test_user.save()

    def test_event_creation(self):
        # Create an event
        Events.objects.create(
            name='Sample Event',
            type_of_location='virtual',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            creator=self.test_user,
        )

        # Get the event
        event = Events.objects.get(id=1)
        expected_name = f'{event.name}'
        expected_type_of_location = f'{event.type_of_location}'
        expected_time_begin = f'{event.time_begin}'
        expected_time_end = f'{event.time_end}'
        expected_creator = f'{event.creator}'

        self.assertEqual(str(event), 'Sample Event')
        self.assertEqual(expected_name, 'Sample Event')
        self.assertEqual(expected_type_of_location, 'virtual')
        self.assertEqual(expected_time_begin, '2021-10-10 10:00:00+00:00')
        self.assertEqual(expected_time_end, '2021-10-10 12:00:00+00:00')
        self.assertEqual(expected_creator, 'testuser')

    def test_event_participant_creation(self):
        # Create an event
        event = Events.objects.create(
            name='Sample Event',
            type_of_location='virtual',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            creator=self.test_user
        )

        # Create an event participant
        event_participant = EventParticipant.objects.create(
            event=event,
            participant=self.test_user,
            role='organizer'
        )

        # Get the event participant
        expected_event = f'{event_participant.event}'
        expected_participant = f'{event_participant.participant}'
        expected_role = f'{event_participant.role}'

        self.assertEqual(str(event_participant), 'testuser - Sample Event')
        self.assertEqual(expected_event, 'Sample Event')
        self.assertEqual(expected_participant, 'testuser')
        self.assertEqual(expected_role, 'organizer')

    def test_event_organizations_creation(self):
        # Create an event
        event = Events.objects.create(
            name='Sample Event',
            type_of_location='virtual',
            time_begin='2021-10-10 10:00:00+00:00',
            time_end='2021-10-10 12:00:00+00:00',
            creator=self.test_user
        )

        # Create an organization
        org_type = OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )
        organization = Organization.objects.create(
            display_name='Sample Organization',
            acronym='SO',
            type=org_type,
        )

        # Create an event organization
        event_organization = EventOrganizations.objects.create(
            event=event,
            organization=organization,
            role='organizer'
        )

        # Get the event organization
        expected_event = f'{event_organization.event}'
        expected_organization = f'{event_organization.organization}'
        expected_role = f'{event_organization.role}'

        self.assertEqual(str(event_organization), 'Sample Organization (SO) - Sample Event')
        self.assertEqual(expected_event, 'Sample Event')
        self.assertEqual(expected_organization, 'Sample Organization (SO)')
        self.assertEqual(expected_role, 'organizer')


