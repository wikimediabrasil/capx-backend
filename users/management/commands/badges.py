from django.core.management.base import BaseCommand
from users.models import Profile, Badge, UserBadge
from users.serializers import ProfileSerializer
from django.conf import settings
import requests

class Command(BaseCommand):
    help = "Recount metrics and attribute or promote new badges to users"

    def add_arguments(self, parser):
        parser.add_argument(
            '--recount',
            action='store_true',
            help='Recount metrics and attribute or promote new badges to users'
        )

    def handle(self, *args, **options):
        if options['recount']:
            self.recount_metrics()

    def recount_metrics(self):
        profiles = Profile.objects.all()
        for profile in profiles:
            self.attribute_or_promote_badges(profile)

    def attribute_or_promote_badges(self, profile):
        # Example logic for attributing or promoting badges based on metrics
        if profile.skills_known.count() > 5:
            badge, created = Badge.objects.get_or_create(name='Skill Master', defaults={
                'picture': 'path/to/skill_master.png',
                'description': 'Awarded for knowing more than 5 skills'
            })
            UserBadge.objects.get_or_create(profile=profile, badge=badge)

        if profile.skills_available.count() > 3:
            badge, created = Badge.objects.get_or_create(name='Generous Teacher', defaults={
                'picture': 'path/to/generous_teacher.png',
                'description': 'Awarded for being available to teach more than 3 skills'
            })
            UserBadge.objects.get_or_create(profile=profile, badge=badge)

        # Add more logic for other badges as needed

    def fetch_external_badges(self):
        response = requests.get(settings.EXTERNAL_BADGES_URL)
        if response.status_code == 200:
            return response.json()
        return []

    def save_external_badges(self):
        external_badges = self.fetch_external_badges()
        for badge_data in external_badges:
            badge, created = Badge.objects.get_or_create(
                name=badge_data['name'],
                defaults={
                    'picture': badge_data['picture'],
                    'description': badge_data['description']
                }
            )
            for username in badge_data['users']:
                profile = Profile.objects.filter(user__username=username).first()
                if profile:
                    UserBadge.objects.get_or_create(profile=profile, badge=badge)

    def handle_badge_replacement(self, profile, new_badge):
        # Logic to handle badge replacement
        existing_badges = UserBadge.objects.filter(profile=profile, badge__name__startswith=new_badge.name.split()[0])
        for existing_badge in existing_badges:
            existing_badge.delete()
        UserBadge.objects.create(profile=profile, badge=new_badge)