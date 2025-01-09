from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.dispatch import receiver
from django.utils import timezone
from django.db.models.signals import post_save
from orgs.models import Organization
from skills.models import Skill
from users.submodels import Territory, Language, WikimediaProject
from django.core.validators import RegexValidator


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        "Username",
        max_length=100,
        unique=True
    )
    email = models.EmailField(
        "Email address",
        max_length=255,
        null=True,
        blank=True
    )
    is_staff = models.BooleanField(
        "Staff status",
        default=False
    )
    is_active = models.BooleanField(
        "Active",
        default=True
    )
    date_joined = models.DateTimeField(
        "Date joined",
        default=timezone.now
    )
    user_groups = models.JSONField(
        null=True,
        blank=False
    )

    objects = UserManager()
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'


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
    profile_image = models.URLField(
        verbose_name="Profile image",
        null=True,
        help_text="URL of the profile image from Commons.",
        blank=True
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
        blank=True
    )

    # COMMUNITY
    territory = models.ManyToManyField(
        Territory,
        verbose_name="Territory",
        related_name="user_territory",
        help_text="ID of the territory that the user is based in.",
        blank=True)
    language = models.ManyToManyField(
        Language,
        through="LanguageProficiency",
        verbose_name="Language",
        related_name="user_language",
        help_text="ID of the language that the user speaks.",
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
        related_name="user_known_skils",
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
        related_name="user_desired_skils",
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

    def __str__(self):
        return self.user.username


class LanguageProficiency(models.Model):
    PROFICIENCY_LEVELS = [
        (0, '0 - No proficiency'),
        (1, '1 - Elementary proficiency'),
        (2, '2 - Limited working proficiency'),
        (3, '3 - Professional working proficiency'),
        (4, '4 - Full professional proficiency'),
        (5, '5 - Native or bilingual proficiency'),
        ('n', 'n - Native'),
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
