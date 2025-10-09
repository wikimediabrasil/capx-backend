from django.db import models
from django.conf import settings


class PortalUser(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    authorizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='authorized_users',
    )
    authorized_at = models.DateTimeField(auto_now_add=True)
    is_authorized = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = 'authorized' if self.is_authorized else 'revoked'
        return f"PortalUser({self.user.username}, {status})"