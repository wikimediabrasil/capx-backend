from django.core.management.base import BaseCommand
from users.models import CustomUser, Badge, UserBadge
from django.apps import apps
from django.db.models import F, Q, Value
from django.utils.timezone import now
from datetime import timedelta
from message.models import Message
from orgs.models import Organization
from users.letsconnect import LetsConnectLog

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
            return 100 if Organization.objects.filter(manager=user).exists() else 0
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
