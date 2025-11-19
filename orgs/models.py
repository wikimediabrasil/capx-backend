from django.db import models
from users.models.reference import Territory
from django.core.validators import RegexValidator
from django.utils import timezone as timezone
from skills.models import Skill


class OrganizationType(models.Model):
    type_code = models.CharField(max_length=20, unique=True)
    type_name = models.CharField(max_length=140)

    def __str__(self):
        return self.type_name


class Organization(models.Model):
    profile_image = models.URLField(
        blank=True, null=True,
        max_length=512,
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
        'users.CustomUser', related_name='managers', blank=True, through='Management',
        help_text='ID of users who are managers of the organization on the platform.'
    )
    meta_page = models.URLField(
        blank=True, null=True,
        max_length=512,
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
        max_length=512,
        help_text='The URL of the organization website.',
    )
    report = models.URLField(
        blank=True, null=True,
        max_length=512,
        help_text='The URL of the organization report.',
    )
    mastodon = models.URLField(
        blank=True, null=True,
        max_length=512,
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
        max_length=512,
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
        name_en = self.i18n_names.filter(language_code='en').first()
        return f"{name_en.name}" if name_en else f"Organization {self.pk}"


class Management(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        help_text='The organization managed by the user.'
    )
    user = models.ForeignKey(
        'users.CustomUser', on_delete=models.CASCADE,
        help_text='The user who manages the organization.'
    )
    joined_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} manages {self.organization}"

class TagDiff(models.Model):
    tag = models.CharField(max_length=255, unique=True)
    creation_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.tag

class Document(models.Model):
    url = models.URLField(
        help_text='The URL of the document on Wikimedia Commons.',
        max_length=512,
        validators=[RegexValidator(
            regex=r'^https:\/\/commons\.wikimedia\.org\/wiki\/File:.*?\.[\w]+$',
            message='Invalid URL format. The format should be https://commons.wikimedia.org/wiki/File:filename.ext'
        )]
    )
    creation_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.url.split('/')[-1].replace('_', ' ')


class OrganizationName(models.Model):
    """Normalized translations for Organization.

    Each row stores the display name for a specific language.
    """
    organization = models.ForeignKey(
        'orgs.Organization',
        on_delete=models.CASCADE,
        related_name='i18n_names',
        help_text='The organization this translation belongs to.'
    )
    language_code = models.CharField(
        max_length=10,
        help_text='BCP 47 / ISO language code (e.g. en, pt-BR).'
    )
    name = models.CharField(
        max_length=255,
        help_text='Localized display name for the organization.'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'language_code'], name='uniq_org_lang_display_name'),
        ]
        indexes = [
            models.Index(fields=['organization', 'language_code']),
        ]

    def __str__(self):
        return f"{self.organization_id}:{self.language_code}={self.name}"