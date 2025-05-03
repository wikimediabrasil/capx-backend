from django.core.management.base import BaseCommand
from users.models import CustomUser
import requests

class Command(BaseCommand):
    help = 'Check if Wikimedia usernames are locked and deactivate them locally'

    def handle(self, *args, **kwargs):
        users = CustomUser.objects.all()
        for user in users:
            params = {
                'action': 'query',
                'meta': 'globaluserinfo',
                'guiuser': user.username,
                'format': 'json',
                'formatversion': '2',
            }

            try:
                response = requests.get('https://meta.wikimedia.org/w/api.php', params=params)
                response.raise_for_status()  # Raise an error for bad responses
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error fetching data for user {user.username}: {e}'))
                continue
            
            data = response.json()
            user_info = data['query']['globaluserinfo']
            if 'locked' in user_info and user_info['locked']:
                user.is_active = False
                user.save()
                self.stdout.write(self.style.SUCCESS(f'User {user.username} is locked and has been deactivated.'))
            else:
                self.stdout.write(self.style.NOTICE(f'User {user.username} is not locked.'))
        self.stdout.write(self.style.SUCCESS('All users have been checked.'))