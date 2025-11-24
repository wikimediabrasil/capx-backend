from django.conf import settings
from django.db import models
import uuid
from datetime import timedelta
from django.utils import timezone


def generate_state():
    """Generate a unique hex state string for OAuth requests."""
    return uuid.uuid4().hex


class MetabaseOAuthToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='metabase_oauth')
    access_token = models.CharField(max_length=255)
    access_secret = models.CharField(max_length=255)
    mb_username = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Metabase OAuth for {self.user} ({self.mb_username or 'unknown'})"


class MetabaseOAuthRequest(models.Model):
    """Transient OAuth 1.0a request token info to identify user at callback.
    Cleaned opportunistically (>15 min old) when new requests are created.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='metabase_oauth_requests')
    state = models.CharField(max_length=64, unique=True, default=generate_state)
    request_token = models.CharField(max_length=255, unique=True)
    request_secret = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    consumed = models.BooleanField(default=False)

    def is_stale(self) -> bool:
        return self.created_at < timezone.now() - timedelta(minutes=15)

    def __str__(self):
        return f"OAuthRequest {self.state} for {self.user}"
