from django.db import models
from django.core.exceptions import ValidationError

from orgs.models import Organization
from .account import CustomUser


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
            return f"{self.user.username}: {self.relation} - Organization - {self.related_org.acronym}"
        elif self.related_user:
            return f"{self.user.username}: {self.relation} - User - {self.related_user.username}"
        return f"{self.user.username}: {self.relation}"


class LetsConnectLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    confirmation = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)
