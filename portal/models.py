from django.db import models
from django.conf import settings


class Partner(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PartnerMembership(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='partner_memberships')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('partner', 'user')

    def __str__(self):
        return f"{self.user.username} @ {self.partner.name}"