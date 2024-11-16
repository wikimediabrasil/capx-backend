from django.db import models
from users.models import Profile, CustomUser
from django.conf import settings
from orgs.models import Organization
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import requests


class Events(models.Model):
    LOCATION_TYPES = [
        ("virtual", "Virtual"),
        ("in_person", "In Person"),
        ("hybrid", "Hybrid"),
    ]
    name = models.CharField(
        max_length=128, 
        verbose_name="Event Name",
        help_text="Name of the event."
    )
    type_of_location = models.CharField(
        choices=LOCATION_TYPES, 
        max_length=20, 
        verbose_name="Type of Location",
        help_text="Type of location of the event."
    )
    openstreetmap_id = models.URLField(
        blank=True, 
        verbose_name="OpenStreetMap ID",
        help_text="OpenStreetMap ID of the event location.",
        validators=[RegexValidator(
            regex=r'^https://www\.openstreetmap\.org/(node|way|relation)/\d+$',
            message="Invalid OpenStreetMap ID format. The format should be https://www.openstreetmap.org/(way|node|relation)/12345"
        )]
    )
    url = models.URLField(
        blank=True,
        verbose_name="Event URL",
        help_text="URL of the event."
    )
    wikilearn_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Wikilearn ID",
        help_text="Wikilearn ID of the event.",
    )
    wikidata_qid = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Wikidata Qid",
        help_text="Wikidata Qid of the event.",
        validators=[RegexValidator(
            regex=r'^Q[1-9]\d*$',
            message="Invalid Wikidata Qid format. The format should be Q12345"
        )]
    )
    image_url = models.URLField(
        blank=True, 
        verbose_name="Image URL",
        help_text="URL of the event image on Wikimedia Commons.",
        validators=[RegexValidator(
            regex=r'^https://commons\.wikimedia\.org/wiki/File:.+$',
            message="Invalid Wikimedia Commons URL format. The format should be https://commons.wikimedia.org/wiki/File:Example.jpg"
        )]
    )
    time_begin = models.DateTimeField(
        verbose_name="Start Time",
        help_text="Start time of the event."
    )
    time_end = models.DateTimeField(
        verbose_name="End Time",
        help_text="End time of the event.",
        blank=True
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="events_created",
        verbose_name="Event Creator",
        help_text="Creator of the event."
    )
    team = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="EventParticipant",
        related_name="team_members",
        verbose_name="Event Team",
        help_text="Team members of the event."
    )
    organizations = models.ManyToManyField(
        Organization,
        through="EventOrganizations",
        verbose_name="Event Organizations",
        help_text="Organizations of the event."
    )
    related_skills = models.ManyToManyField(
        "skills.Skill",
        blank=True,
        verbose_name="Related Skills",
        help_text="Skills related to the event."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Time when the event was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Time when the event was last updated."
    )

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.wikilearn_id:
            api_url = f"https://learn.wiki/api/courses/v1/courses/{self.wikilearn_id}"
            response = requests.get(api_url)
            if response.status_code != 200:
                raise ConnectionError("Wikilearn service is not available.")

            data = response.json()
            
            if not data.get("id"):
                raise ValueError("Invalid Wikilearn ID.")

            self.name = data.get("name")
            self.time_begin = data.get("start")
            self.time_end = data.get("end") if data.get("end") else ""
            self.url = f"https://learn.wiki/courses/{self.wikilearn_id}/about"

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    
class EventParticipant(models.Model):
    ROLE_TYPES = [
        ("organizer", "Organizer"),
        ("committee", "Committee"),
        ("volunteer", "Volunteer"),
    ]
    event = models.ForeignKey(
        Events,
        on_delete=models.CASCADE,
        help_text="Event of the participant."
    )
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="Account of the participant."
    )
    role = models.CharField(
        choices=ROLE_TYPES,
        max_length=20,
        help_text="Role of the participant."
    )
    confirmed_organizer = models.BooleanField(
        default=False,
        help_text="Is the participation confirmed by the organizer?"
    )
    confirmed_participant = models.BooleanField(
        default=False,
        help_text="Is the participation confirmed by the participant?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Time when the participation was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Time when the participation was last updated."
    )

    def __str__(self):
        return f"{self.participant} - {self.event}"
    
class EventOrganizations(models.Model):
    ROLE_TYPES = [
        ("organizer", "Organizer"),
        ("sponsor", "Sponsor"),
        ("supporter", "Supporter"),
    ]
    event = models.ForeignKey(
        Events,
        on_delete=models.CASCADE,
        help_text="Event where the organization is part of."
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        help_text="Organization which is part of the event."
    )
    role = models.CharField(
        choices=ROLE_TYPES,
        max_length=20,
        help_text="Role of the organization."
    )
    confirmed_organizer = models.BooleanField(
        default=False,
        help_text="Is the participation confirmed by the organizer?"
    )
    confirmed_organization = models.BooleanField(
        default=False,
        help_text="Is the participation confirmed by the organization?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Time when the participation was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Time when the participation was last updated."
    )

    def __str__(self):
        return f"{self.organization} - {self.event}"