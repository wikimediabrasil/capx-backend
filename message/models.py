from django.db import models
from django.conf import settings
from requests_oauthlib import OAuth1Session
from social_django.models import UserSocialAuth


class MessageManager(models.Manager):
    def send_message(self, instance):
        url = 'https://meta.wikimedia.org/w/api.php'
        user_social_auth = UserSocialAuth.objects.get(user=instance.sender)
        oauth = OAuth1Session(
            settings.SOCIAL_AUTH_MEDIAWIKI_KEY,
            client_secret=settings.SOCIAL_AUTH_MEDIAWIKI_SECRET,
            resource_owner_key=user_social_auth.extra_data['access_token']['oauth_token'],
            resource_owner_secret=user_social_auth.extra_data['access_token']['oauth_token_secret']
        )

        # Get tokens
        params_token = {
            'action': 'query',
            'meta': 'tokens',
            'format': 'json',
            'formatversion': '2',
        }
        reply = oauth.get(url, params=params_token, timeout=60)
        token = reply.json().get('query', {}).get('tokens', {}).get('csrftoken', '')

        if not token:
            instance.status = 'failed'
            instance.save()
            return

        params_emailable = {
            'action': 'query',
            'format': 'json',
            'list': 'users',
            'formatversion': '2',
            'usprop': 'emailable',
            'ususers': instance.receiver,
        }
        reply = oauth.get(url, params=params_emailable, timeout=60)
        if reply.json().get('query', {}).get('users', [{}])[0].get('emailable', False):
            params_send = {
                'action': 'emailuser',
                'target': instance.receiver,
                'subject': instance.message[:50],  # Assuming the first 50 chars as the subject
                'text': instance.message,
                'ccme': '1',
                'format': 'json',
                'token': token,
            }
            reply = oauth.post(url, data=params_send, timeout=60)
            if reply.json().get('emailuser', {}).get('result') == 'Success':
                instance.status = 'sent'
            else:
                instance.status = 'failed'
            instance.save()
        else:
            params_send = {
                'action': 'edit',
                'title': f'User talk:{instance.receiver}',
                'section': 'new',
                'sectiontitle': instance.message[:50],  # Assuming the first 50 chars as the section title
                'text': instance.message,
                'format': 'json',
                'token': token,
            }
            reply = oauth.post(url, data=params_send, timeout=60)
            if reply.json().get('edit', {}).get('result') == 'Success':
                instance.status = 'sent'
            else:
                instance.status = 'failed'
            instance.save()

class Message(models.Model):
    MESSAGE_METHOD = (
        ('email', 'Email'),
        ('talkpage', 'Talkpage'),
    )
    message = models.CharField(max_length=500)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sender')
    receiver = models.CharField(max_length=100)
    method = models.CharField(max_length=10, choices=MESSAGE_METHOD)
    status = models.CharField(max_length=10, default='pending')
    date = models.DateTimeField(auto_now_add=True)

    objects = MessageManager()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.status = 'sending'
            self.save(update_fields=['status'])
            Message.objects.send_message(self)

    def __str__(self):
        return f'{self.sender} to {self.receiver} - {self.date.strftime("%d/%m/%Y %H:%M:%S")}'