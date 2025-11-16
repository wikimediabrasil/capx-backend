from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.utils import timezone


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
    all_objects = UserManager()  # Access to all users if needed
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
