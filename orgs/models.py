from django.db import models
from users.submodels import Territory
from django.core.validators import RegexValidator
from django.utils import timezone as timezone
from skills.models import Skill


class OrganizationType(models.Model):
    type_code = models.CharField(max_length=20, unique=True)
    type_name = models.CharField(max_length=140)

    def __str__(self):
        return self.type_name


class Organization(models.Model):
    display_name = models.CharField(
        max_length=255,
        help_text='The full name of the organization.',
    )
    profile_image = models.URLField(
        blank=True, null=True,
        help_text='The URL of the organization profile image on Wikimedia Commons.',
        validators=[RegexValidator(
            regex=r'^https:\/\/commons\.wikimedia\.org\/wiki\/File:.*?\.[\w]+$',
            message='Invalid URL format. The format should be https://commons.wikimedia.org/wiki/File:filename.ext'
        )]
    )
    acronym = models.CharField(
        max_length=10, unique=True,
        help_text='The acronym of the organization (if any).',
    )
    type = models.ForeignKey(
        OrganizationType, on_delete=models.RESTRICT, null=True, 
        help_text='The type of the organization as defined in the OrganizationType model.',
    )
    territory = models.ManyToManyField(
        Territory, blank=True, related_name='territory',
        help_text='The territories where the organization is active.'
    )
    managers = models.ManyToManyField(
        'users.CustomUser', related_name='managers', blank=True,
        help_text='ID of users who are managers of the organization on the platform.'
    )
    meta_page = models.URLField(
        blank=True, null=True,
        help_text='The URL of the organization page on Meta-Wiki.',
        validators=[RegexValidator(
            regex=r'^https:\/\/meta\.wikimedia\.org\/wiki\/.*?$',
            message='Invalid URL format. The format should be https://meta.wikimedia.org/wiki/PageName'
        )]
    )
    email = models.EmailField(
        blank=True, null=True,
        help_text='The email address of the organization.',
    )
    website = models.URLField(
        blank=True, null=True,
        help_text='The URL of the organization website.',
    )
    report = models.URLField(
        blank=True, null=True,
        help_text='The URL of the organization report.',
    )
    mastodon = models.URLField(
        blank=True, null=True,
        help_text='The URL of the organization Mastodon account.',
    )
    tag_diff = models.ManyToManyField(
        'orgs.TagDiff', related_name='tag_diff', blank=True,
        help_text='The tag used by the organization on Diff posts (if any).',
    )
    documents = models.ManyToManyField(
        'orgs.Document', related_name='documents', blank=True,
        help_text='The documents related to the organization.',
    )
    choose_events = models.ManyToManyField(
        'events.Events', 
        related_name='highlighted_by_organizations',
        blank=True,
        help_text='Highlighted events chosen by the organization.',
    )
    home_project = models.URLField(
        blank=True, null=True, 
        help_text='The URL of the home project of the organization on Wikimedia (e.g. https://xx.wikimedia.org/).',
        validators=[RegexValidator(
        regex=r'^https:\/\/[\w-]+\.wikimedia\.org\/$',
        message='Invalid URL format. The format should be https://xx.wikimedia.org/'
    )])
    known_capacities = models.ManyToManyField(
        Skill,
        verbose_name="Known capacities",
        related_name="known_capacities",
        help_text="The known capacities of the organization.",
        blank=True
    )
    available_capacities = models.ManyToManyField(
        Skill,
        verbose_name="Available capacities",
        related_name="available_capacities",
        help_text="The available capacities of the organization.",
        blank=True
    )
    wanted_capacities = models.ManyToManyField(
        Skill,
        verbose_name="Wanted capacities",
        related_name="wanted_capacities",
        help_text="The wanted capacities of the organization.",
        blank=True
    )
    update_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        if self.acronym:
            return self.display_name + " (" + self.acronym + ")"
        else:
            return self.display_name

class TagDiff(models.Model):
    tag = models.CharField(max_length=255, unique=True)
    creation_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.tag

class Document(models.Model):
    url = models.URLField(
        help_text='The URL of the document on Wikimedia Commons.',
        validators=[RegexValidator(
            regex=r'^https:\/\/commons\.wikimedia\.org\/wiki\/File:.*?\.[\w]+$',
            message='Invalid URL format. The format should be https://commons.wikimedia.org/wiki/File:filename.ext'
        )]
    )
    creation_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.url.split('/')[-1].replace('_', ' ')