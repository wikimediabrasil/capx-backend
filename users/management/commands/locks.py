from django.core.management.base import BaseCommand
import requests

class Command(BaseCommand):
    help = 'Check if Wikimedia usernames are locked and unactivate them locally'

    def handle(self, *args, **kwargs):
        from users.models import CustomUser

        # Get all users with a Wikimedia username
        users = CustomUser.objects.all()
        for user in users:
            # Check if the username is locked
            params = {
                'action': 'query',
                'meta': 'globaluserinfo',
                'guiuser': user.username,
                'format': 'json',
                'formatversion': '2',
            }
            response = requests.get('https://meta.wikimedia.org/w/api.php', params=params)
            data = response.json()
            if 'globaluserinfo' in data['query']:
                user_info = data['query']['globaluserinfo']
                if 'locked' in user_info and user_info['locked']:
                    # Unactivate the user locally
                    user.is_active = False
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'User {user.username} is locked and has been deactivated.'))
                else:
                    self.stdout.write(self.style.NOTICE(f'User {user.username} is not locked.'))
            else:
                self.stdout.write(self.style.WARNING(f'User {user.username} not found in Wikimedia.'))
        self.stdout.write(self.style.SUCCESS('All users have been checked.'))