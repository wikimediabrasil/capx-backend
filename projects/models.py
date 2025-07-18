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
        max_length=512,
        help_text='The URL of the project profile image on Wikimedia Commons.',
        validators=[RegexValidator(
            regex=r'^https:\/\/commons\.wikimedia\.org\/wiki\/File:.*?\.[\w]+$',
            message='Invalid URL format. The format should be https://commons.wikimedia.org/wiki/File:filename.ext'
        )]
    )
    description = models.TextField(
        blank=True, null=True,
        help_text='The description of the project.'
    )
    url = models.URLField(
        blank=True, null=True,
        max_length=512,
        help_text='The URL of the project.',
    )
    related_skills = models.ManyToManyField(
        'skills.Skill', related_name='related_skills', blank=True,
        help_text='The skills related to the project.'
    )
    creator = models.ForeignKey(
        'users.CustomUser', on_delete=models.RESTRICT, null=True,
        help_text='The ID of the user who added the project on the platform.'
    )
    creation_date = models.DateTimeField(
        default=timezone.now,
        help_text='The date when the project was added on the platform.'
    )

    def __str__(self):
        return self.display_name

class ProjectMember(models.Model):
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, related_name='organizations',
        help_text='The ID of the project.'
    )
    organization = models.ForeignKey(
        'orgs.Organization', on_delete=models.CASCADE,
        help_text='The ID of the organization.'
    )

class ProjectMemberAcceptance(models.Model):
    project_member = models.ForeignKey(
        'projects.ProjectMember', on_delete=models.CASCADE,
        help_text='The ID of the project member.'
    )
    accepted = models.BooleanField(
        default=False,
        help_text='The status of the project member.'
    )
    date = models.DateTimeField(
        default=timezone.now,
        help_text='The date when the project member was accepted.'
    )