from django.db import models

from .account import CustomUser


class Badge(models.Model):
    BADGE_TYPE_CHOICES = [
        ("internal", "Internal"),
        ("external", "External"),
        ("partner", "Partner"),
    ]
    name = models.CharField(max_length=255)
    picture = models.URLField(max_length=512)
    description = models.TextField()
    logic = models.JSONField(null=True, blank=True, help_text="Logic fields for badge criteria.")
    type = models.CharField(max_length=10, choices=BADGE_TYPE_CHOICES, default="internal")

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0, help_text="Progress towards the badge.")
    is_displayed = models.BooleanField(default=True)
    external_assertion_url = models.URLField(max_length=512, null=True, blank=True)
    external_issued_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"
