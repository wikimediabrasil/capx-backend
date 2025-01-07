from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone

class Project(models.Model):
    display_name = models.CharField(
        max_length=255,
        help_text='The full name of the project.',
    )
    profile_image = models.URLField(
        blank=True, null=True,
        help_text='The URL of the project profile image on Wikimedia Commons.',
        validators=[RegexValidator(
            regex=r'^https:\/\/commons\.wikimedia\.org\/wiki\/File:.*?\.[\w]+$',
            message='Invalid URL format. The format should be https://commons.wikimedia.org/wiki/File:filename.ext'
        )]
    )
    url = models.URLField(
        blank=True, null=True,
        help_text='The URL of the project.',
    )
    organizations = models.ManyToManyField(
        'orgs.Organization', related_name='organizations', blank=True,
        help_text='The organizations that are part of the project.'
    )
    creator = models.ForeignKey(
        'users.CustomUser', on_delete=models.RESTRICT, null=True,
        help_text='The ID of the user who added the project on the platform.'
    )
    creation_date = models.DateTimeField(
        default=timezone.now,
        help_text='The date when the project was added on the platform.'
    )
