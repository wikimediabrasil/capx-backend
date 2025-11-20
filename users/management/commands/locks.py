from django.core.management.base import BaseCommand
from users.models import CustomUser
from django.conf import settings
import requests
from social_django.models import UserSocialAuth

class Command(BaseCommand):
    help = 'Check if Wikimedia usernames are locked and deactivate them locally'

    def get_user_agent(self):
        version = getattr(settings, "SPECTACULAR_SETTINGS", {}).get("VERSION", "dev")
        return f"CapacityExchangeBot/{version}"

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        users = CustomUser.objects.all()
        for user in users:
            params = {
                'action': 'query',
                'meta': 'globaluserinfo',
                'guiid': UserSocialAuth.objects.filter(user=user, provider='mediawiki').first().uid if UserSocialAuth.objects.filter(user=user, provider='mediawiki').exists() else '',
                'format': 'json',
                'formatversion': '2',
            }

            try:
                response = requests.get('https://meta.wikimedia.org/w/api.php', params=params, headers={'User-Agent': self.get_user_agent()})
                response.raise_for_status()  # Raise an error for bad responses
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error fetching data for user {user.username}: {e}'))
                continue
            
            data = response.json()
            user_info = data['query']['globaluserinfo']
            if 'locked' in user_info and user_info['locked']:
                user.is_active = False
                user.save()
                if self.verbosity >= 2:
                    self.stdout.write(self.style.SUCCESS(f'User {user.username} is locked and has been deactivated.'))
            else:
                if self.verbosity >= 2:
                    self.stdout.write(self.style.NOTICE(f'User {user.username} is not locked.'))