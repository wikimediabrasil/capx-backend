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
        max_length=512,
        verbose_name="OpenStreetMap ID",
        help_text="OpenStreetMap ID of the event location.",
        validators=[RegexValidator(
            regex=r'^https://www\.openstreetmap\.org/(node|way|relation)/\d+$',
            message="Invalid OpenStreetMap ID format. The format should be https://www.openstreetmap.org/(way|node|relation)/12345"
        )]
    )
    url = models.URLField(
        blank=True,
        max_length=512,
        verbose_name="Event URL",
        help_text="URL of the event."
    )
    description = models.TextField(
        blank=True,
        verbose_name="Event Description",
        help_text="Description of the event."
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
        max_length=512,
        verbose_name="Image URL",
        help_text="URL of the event image on Wikimedia Commons or Learn Wiki.",
        validators=[RegexValidator(
            regex=r'^(https://commons\.wikimedia\.org/wiki/File:.+|https://learn\.wiki/asset.+)$',
            message="Invalid URL format. The format should be https://commons.wikimedia.org/wiki/File:Example.jpg or https://learn.wiki/asset..."
        )]
    )
    time_begin = models.DateTimeField(
        verbose_name="Start Time",
        help_text="Start time of the event."
    )
    time_end = models.DateTimeField(
        verbose_name="End Time",
        help_text="End time of the event.",
        blank=True,
        null=True
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="events_created",
        verbose_name="Event Creator",
        help_text="Creator of the event."
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Event Organization",
        help_text="Organization associated with the event."
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
