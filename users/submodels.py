from django.db import models

class Territory(models.Model):
    territory_name = models.CharField(
        verbose_name="Territory name", 
        max_length=128, 
        unique=True,
        help_text="Name of the territory"    
    )
    parent_territory = models.ManyToManyField(
        "self", 
        verbose_name="Parent territory", 
        symmetrical=False,
        related_name="territory_parent", 
        blank=True,
        help_text="Parent territory of the territory"
    )

    def __str__(self):
        return self.territory_name


class Language(models.Model):
    language_name = models.CharField(
        verbose_name="Language name", 
        max_length=128,
        help_text="Name of the language (in English)"
    )
    language_autonym = models.CharField(
        verbose_name="Language autonym", 
        max_length=128, 
        blank=True,
        help_text="Name of the language in the language itself"
    )
    language_code = models.CharField(
        verbose_name="Language code", 
        max_length=10, 
        unique=True,
        help_text="Code of the language"
    )

    def __str__(self):
        return self.language_name


class WikimediaProject(models.Model):
    wikimedia_project_name = models.CharField(
        verbose_name="Wikimedia project name",
        max_length=128,
        help_text="Name of the Wikimedia project"
    )
    wikimedia_project_code = models.CharField(
        verbose_name="Wikimedia project code",
        max_length=40,
        unique=True,
        help_text="Code of the Wikimedia project"
    )
    wikimedia_project_picture = models.URLField(
        verbose_name="Wikimedia project picture",
        max_length=255,
        blank=True,
        help_text="Picture of the Wikimedia project"
    )

    def __str__(self):
        return self.wikimedia_project_name


class Avatar(models.Model):
    avatar_url = models.URLField(
        verbose_name="Avatar URL",
        help_text="URL of the avatar"
    )

    def __str__(self):
        return self.avatar_url


class AuthExtraInfo(models.Model):
    token = models.CharField(
        verbose_name="Oauth token",
        max_length=255,
    )
    extra = models.CharField(
        verbose_name="Extra info",
        max_length=255,
    )
    created_at = models.DateTimeField(
        verbose_name="Created at",
        auto_now_add=True
    )