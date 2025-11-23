from django.core.management.base import BaseCommand
from users.models import CustomUser
import requests
from social_django.models import UserSocialAuth
from CapX.useragent import get_user_agent

class Command(BaseCommand):
    help = 'Check if Wikimedia usernames are locked and deactivate them locally'

    def fetch_user_info(self, mediawiki_auth):
        params = {
            'action': 'query',
            'meta': 'globaluserinfo',
            'guiid': mediawiki_auth.uid if mediawiki_auth else '',
            'format': 'json',
            'formatversion': '2',
        }
        response = requests.get(
            'https://meta.wikimedia.org/w/api.php',
            params=params,
            headers={'User-Agent': get_user_agent('Locks')}
        )
        response.raise_for_status()
        data = response.json()
        return data.get('query', {}).get('globaluserinfo', {})

    def rename_user_if_needed(self, user, remote_name):
        if not remote_name or remote_name == user.username:
            return
        # Collision check including inactive users
        if CustomUser.all_objects.filter(username=remote_name).exclude(pk=user.pk).exists():
            if self.verbosity >= 1:
                self.stdout.write(self.style.WARNING(
                    f'Cannot rename {user.username} -> {remote_name}: username already exists locally.'
                ))
            return
        old_username = user.username
        user.username = remote_name
        user.save(update_fields=['username'])
        if self.verbosity >= 2:
            self.stdout.write(self.style.SUCCESS(f'Renamed local user {old_username} -> {remote_name}'))

    def deactivate_if_locked(self, user, user_info):
        if user_info.get('locked') and user.is_active:
            user.is_active = False
            user.save(update_fields=['is_active'])
            if self.verbosity >= 2:
                self.stdout.write(self.style.SUCCESS(f'User {user.username} is locked and has been deactivated.'))
        elif self.verbosity >= 2:
            notice_style = getattr(self.style, 'NOTICE', self.style.WARNING)
            self.stdout.write(notice_style(f'User {user.username} is not locked.'))

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        for user in CustomUser.objects.all():
            mediawiki_auth = UserSocialAuth.objects.filter(user=user, provider='mediawiki').first()
            try:
                user_info = self.fetch_user_info(mediawiki_auth)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error fetching data for user {user.username}: {e}'))
                continue
            self.rename_user_if_needed(user, user_info.get('name'))
            self.deactivate_if_locked(user, user_info)