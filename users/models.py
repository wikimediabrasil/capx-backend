from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.dispatch import receiver
from django.utils import timezone
from django.db.models.signals import post_save
from orgs.models import Organization
from skills.models import Skill
from users.submodels import Territory, Language, WikimediaProject, Avatar, DataHash
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db.models import Manager


class ActiveUserManager(UserManager):
    """
    Custom manager to filter out inactive users by default.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


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

    objects = ActiveUserManager()  # Use the custom manager
    all_objects = UserManager()  # Add this to access all users if needed
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'


class ActiveProfileManager(Manager):
    """
    Custom manager to filter out profiles linked to inactive users.
    """
    def get_queryset(self):
        return super().get_queryset().filter(user__is_active=True)

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
    avatar = models.ForeignKey(
        'Avatar',
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

    # LAST UPDATE
    last_update = models.DateTimeField(
        verbose_name="Last update",
        auto_now=True,
        help_text="Timestamp of the last update to the profile."
    )

    objects = ActiveProfileManager()  # Use the custom manager
    all_objects = Manager()  # Add this to access all profiles if needed

    def save(self, *args, **kwargs):
        """
        Overrides the save method to set the primary key (pk) of the instance to the
        primary key of the associated user to ensure that both the user and profile
        have the same primary key.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
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


class SavedItem(models.Model):
    RELATION_TYPES = [
        ('learner', 'Learner'),
        ('sharer', 'Sharer'),
    ]
    ENTITY_TYPES = [
        ('user', 'User'),
        ('org', 'Organization'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    relation = models.CharField(max_length=7, choices=RELATION_TYPES)
    entity = models.CharField(max_length=4, choices=ENTITY_TYPES)
    related_org = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="saved_items"
    )
    related_user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="related_saved_items"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """
        Custom validation to ensure that related_org and related_user are set correctly
        based on the entity type and to enforce uniqueness constraints.
        """
        if self.entity == 'org':
            if not self.related_org or self.related_user:
                raise ValidationError("For entity 'org', related_org must be set and related_user must be null.")
            if SavedItem.objects.filter(user=self.user, relation=self.relation, entity='org', related_org=self.related_org).exists():
                raise ValidationError("This combination of user, relation, entity, and related_org already exists.")
        elif self.entity == 'user':
            if not self.related_user or self.related_org:
                raise ValidationError("For entity 'user', related_user must be set and related_org must be null.")
            if SavedItem.objects.filter(user=self.user, relation=self.relation, entity='user', related_user=self.related_user).exists():
                raise ValidationError("This combination of user, relation, entity, and related_user already exists.")
        else:
            raise ValidationError("Invalid entity type.")

    def save(self, *args, **kwargs):
        """
        Overrides the save method to call the clean method for validation
        before saving the instance.
        """
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.related_org:
            return f"{self.user.username}: {self.relation} - Organization - {self.related_org.display_name}"
        elif self.related_user:
            return f"{self.user.username}: {self.relation} - User - {self.related_user.username}"


class Badge(models.Model):
    BADGE_TYPE_CHOICES = [
        ("internal", "Internal"),
        ("external", "External"),
    ]
    name = models.CharField(max_length=255)
    picture = models.URLField()
    description = models.TextField()
    logic = models.JSONField(null=True, blank=True, help_text="Logic fields for badge criteria.")
    type = models.CharField(max_length=10, choices=BADGE_TYPE_CHOICES, default="internal")
    external_id = models.CharField(max_length=255, null=True, blank=True, help_text="ID from external badge provider, if applicable.")

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0, help_text="Progress towards the badge.")
    is_displayed = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class LetsConnectLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    confirmation = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
