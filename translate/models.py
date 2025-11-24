from django.conf import settings
from django.db import models


class MetabaseOAuthToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='metabase_oauth')
    access_token = models.CharField(max_length=255)
    access_secret = models.CharField(max_length=255)
    mb_username = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Metabase OAuth for {self.user} ({self.mb_username or 'unknown'})"
