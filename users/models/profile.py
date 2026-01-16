from django.db import models
from django.db.models import Manager
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import requests

from orgs.models import Organization
from skills.models import Skill
from .reference import Territory, Language, WikimediaProject, Avatar
from .account import CustomUser


class ActiveProfileManager(Manager):
    """
    Custom manager to filter out profiles linked to inactive users.
    """
    def get_queryset(self):
        return super().get_queryset().filter(user__is_active=True)


def validate_wiki_alt(value):
    """Validate that the provided Wikimedia alternative account exists and is not a CapX username.

    Checks:
    1. Username exists on Wikimedia (Meta-Wiki) via MediaWiki API.
    2. Username is not already a primary CapX user account (CustomUser.username).
    """
    if not value:
        return
    try:
        resp = requests.get(
            "https://meta.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "list": "users",
                "ususers": value,
            },
            timeout=5,
            headers={"User-Agent": "CapX/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        users = data.get("query", {}).get("users", [])
        if not users or users[0].get("missing") is not None:
            raise ValidationError("Wikimedia username does not exist.")
    except requests.RequestException:
        raise ValidationError("Unable to reach Wikimedia API to validate username.")

    if CustomUser.objects.filter(username=value).exists():
        raise ValidationError("This username already belongs to a CapX user; cannot set as alternative account.")


class Profile(models.Model):
    PRONOUNS = (
        ("he-him", "He/Him"),
        ("she-her", "She/Her"),
        ("they-them", "They/Them"),
        ("not-specified", "Not specified"),
        ("other", "Other")
    )
    CONTACT_METHODS = (
        ("email", "Email"),
        ("discussion", "Discussion page"),
        ("wiki", "Meta-Wiki talk page"),
        ("IRC", "IRC"),
    )

    # PERSONAL INFORMATION
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        editable=False
    )
    avatar = models.ForeignKey(
        Avatar,
        on_delete=models.RESTRICT,
        verbose_name="Avatar",
        help_text="ID of the avatar that the user uses.",
        null=True,
        default=None
    )
    display_name = models.CharField(
        verbose_name="Display name",
        max_length=387,
        help_text="Display name of the user.",
        blank=True
    )
    pronoun = models.CharField(
        verbose_name="Pronoun",
        max_length=20,
        help_text="Pronoun of the user.",
        choices=PRONOUNS,
        blank=True
    )
    about = models.TextField(
        verbose_name="Short bio",
        max_length=2000,
        blank=True,
        help_text="Short bio of the user.",
        default=""
    )
    about_language = models.ForeignKey(
        Language,
        on_delete=models.RESTRICT,
        verbose_name="Bio language",
        help_text="Language of the user's bio.",
        null=True,
        default=None
    )
    wikidata_qid = models.CharField(
        verbose_name="Wikidata Qid",
        max_length=10,
        help_text="Wikidata Qid of the user.",
        blank=True,
        validators=[RegexValidator(
            regex=r'^Q[1-9]\d*$',
            message="Invalid Wikidata Qid format. The format should be Q12345"
        )]
    )
    wiki_alt = models.CharField(
        verbose_name="Wikimedia alternative account",
        max_length=128,
        help_text="Wikimedia alternative account of the user.",
        blank=True,
        validators=[validate_wiki_alt]
    )

    # COMMUNITY
    territory = models.ManyToManyField(
        Territory,
        verbose_name="Territory",
        related_name="user_territory",
        help_text="ID of the territory that the user is based in.",
        blank=True
    )
    affiliation = models.ManyToManyField(
        Organization,
        verbose_name="Affiliation",
        related_name="user_affiliation",
        help_text="ID of the organization that the user is affiliated with.",
        blank=True
    )
    wikimedia_project = models.ManyToManyField(
        WikimediaProject,
        verbose_name="Wikimedia project",
        related_name="user_wikimedia_project",
        help_text="ID of the Wikimedia project that the user contributes to.",
        blank=True
    )
    team = models.CharField(
        verbose_name="Team",
        max_length=128,
        help_text="Name of the team that the user is part of.",
        blank=True
    )

    # SKILLS
    skills_known = models.ManyToManyField(
        Skill,
        verbose_name="Known capacity",
        related_name="user_known_skills",
        help_text="List of IDs of skills that the user knows.",
        blank=True
    )
    skills_available = models.ManyToManyField(
        Skill,
        verbose_name="Available capacity",
        related_name="user_available_skills",
        help_text="List of IDs of skills that the user is available to teach.",
        blank=True
    )
    skills_wanted = models.ManyToManyField(
        Skill,
        verbose_name="Wanted capacity",
        related_name="user_desired_skills",
        help_text="List of IDs of skills that the user wants to learn.",
        blank=True
    )

    # CONTACT
    contact = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Contact methods",
        help_text="json"
    )
    social = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Social medias",
        help_text="json"
    )

    # LAST UPDATE
    last_update = models.DateTimeField(
        verbose_name="Last update",
        auto_now=True,
        help_text="Timestamp of the last update to the profile."
    )

    # TEMPORARY FOR LETS CONNECT INTEGRATION
    automated_lets_connect = models.BooleanField(
        "Automated lets connect",
        null=True,
        blank=True,
        default=None,
        help_text="Temporary field indicating whether the user has automated lets connect integration."
    )

    objects = ActiveProfileManager()  # Use the custom manager
    all_objects = Manager()  # Access to all profiles if needed

    def save(self, *args, **kwargs):
        """
        Ensure the profile's pk matches the user's pk when first created.
        """
        if not self.pk and self.user:
            self.pk = self.user.pk
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username


class LanguageProficiency(models.Model):
    PROFICIENCY_LEVELS = [
        (0, '0 - No proficiency'),
        (1, '1 - Basic proficiency'),
        (2, '2 - Intermediate proficiency'),
        (3, '3 - Advanced proficiency'),
        (4, '4 - "Near-native" proficiency'),
        (5, '5 - Professional proficiency'),
        ('n', 'n - Native proficiency'),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    proficiency = models.CharField(max_length=1, choices=PROFICIENCY_LEVELS, blank=True)

    class Meta:
        unique_together = ('profile', 'language')

    def __str__(self):
        return f"{self.profile.user.username} - {self.language.language_name}"


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        # Blank any existing wiki_alt matching this new username to avoid duplicity
        Profile.all_objects.filter(wiki_alt=instance.username).exclude(user=instance).update(wiki_alt="")
