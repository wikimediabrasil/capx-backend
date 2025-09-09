from django.core.management.base import BaseCommand
from users.models import CustomUser, Badge, UserBadge
from django.apps import apps
from django.db.models import F, Q, Value
from django.utils.timezone import now
from datetime import timedelta
from message.models import Message
from orgs.models import Organization
from users.letsconnect import LetsConnectLog
import requests

class Command(BaseCommand):
    help = "Recount metrics and attribute or promote new badges to users"

    def handle(self, *args, **kwargs):
        badges = Badge.objects.all()
        users = CustomUser.objects.all()

        for badge in badges:
            logic = badge.logic
            if not logic or badge.type == 'external':
                continue

            for user in users:
                UserBadge.objects.update_or_create(
                    user=user,
                    badge=badge,
                    defaults={
                        'progress': self.evaluate_logic(logic, user),
                    },
                )
        
        for user in users:
            main_username = user.username
            api = f"https://learn.wiki/api/badges/v1/assertions/user/{main_username}/"
            response = requests.get(api)
            if response.status_code == 200 and response.json().get('results', None):
                for badge in response.json().get('results'):
                    ext_badge, _ = Badge.objects.get_or_create(
                        name=badge['badge_class']['display_name'],
                        description=badge['badge_class']['description'],
                        type='external',
                        logic={'source': 'wikilearn'},
                        defaults={
                            'picture': badge['image_url'] or 'https://badgr.com/f18f753bfdf0c057.svg',
                        }
                    )
                    UserBadge.objects.update_or_create(
                        user=user,
                        badge=ext_badge,
                        defaults={
                            'progress': 100,
                            'external_assertion_url': badge['assertion_url'],
                            'external_issued_on': badge['created']
                        }
                    )

            api2 = f"https://letsconn.toolforge.org/user-badges/?username={main_username}"
            response2 = requests.get(api2)
            if response2.status_code == 200:
                for badge in response2.json():
                    ext_badge, _ = Badge.objects.get_or_create(
                        name=badge['name'],
                        description=badge['description'],
                        type='external',
                        logic={'source': 'letsconnect'},
                        defaults={
                            'picture': badge['picture'] or None,
                        }
                    )
                    UserBadge.objects.update_or_create(
                        user=user,
                        badge=ext_badge,
                        defaults={
                            'progress': 100,
                            'external_assertion_url': f"https://letsconn.toolforge.org/badge/{badge['verification_code']}/",
                            'external_issued_on': badge['timestamp']
                        }
                    )

    def evaluate_logic(self, logic, user):

        target = logic.get('target')
        value = int(logic.get('value'))

        if target == 'sent_messages':
            sent = Message.objects.filter(sender=user).count()
            return min((sent / value) * 100, 100) if value else 0
        elif target == 'received_messages':
            received = Message.objects.filter(receiver=user).count()
            return min((received / value) * 100, 100) if value else 0
        elif target == 'updated_profile':
            last_update = user.profile.last_update
            deadline = now() - timedelta(days=value)
            diff = last_update > deadline
            return 100 if diff else 0
        elif target == 'is_manager':
            return 100 if Organization.objects.filter(managers=user).exists() else 0
        elif target == 'complete_profile':
            fields = sum([
                user.profile.territory.exists(),
                user.profile.affiliation.exists(),
                user.profile.wikimedia_project.exists(),
                user.profile.skills_known.exists(),
                user.profile.skills_available.exists(),
                user.profile.skills_wanted.exists()
            ])
            return fields / 6 * 100 if fields else 0
        elif target == 'account_age':
            created_at = user.date_joined
            deadline = now() - timedelta(days=value)
            diff = created_at < deadline
            return 100 if diff else 0
        elif target == 'lets_connect':
            return 100 if LetsConnectLog.objects.filter(user=user).exists() else 0
