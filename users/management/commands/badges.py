from django.core.management.base import BaseCommand
from users.models import Profile, Badge, UserBadge
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
        profiles = Profile.objects.all()

        for badge in badges:
            logic = badge.logic
            if not logic or badge.type == 'external':
                continue

            for profile in profiles:
                UserBadge.objects.update_or_create(
                    profile=profile,
                    badge=badge,
                    defaults={
                        'progress': self.evaluate_logic(logic, profile),
                    },
                )

    def evaluate_logic(self, logic, profile):
        
        target = logic.get('target')
        value = int(logic.get('value'))

        if target == 'sent_messages':
            sent = Message.objects.filter(sender=profile.user).count()
            return min((sent / value) * 100, 100) if value else 0
        elif target == 'received_messages':
            received = Message.objects.filter(receiver=profile.user).count()
            return min((received / value) * 100, 100) if value else 0
        elif target == 'updated_profile':
            updated_at = profile.updated_at
            return min((now() - updated_at).days / value, 1) * 100 if value else 0
        elif target == 'is_manager':
            return 100 if Organization.objects.filter(manager=profile.user).exists() else 0
        elif target == 'complete_profile':
            return all([
                profile.territory.exists(),
                profile.affiliation.exists(),
                profile.wikimedia_project.exists(),
                profile.skills_known.exists(),
                profile.skills_available.exists(),
                profile.skills_wanted.exists()
            ])
        elif target == 'account_age':
            created_at = profile.user.date_joined
            return min((now() - created_at).days / value, 1) * 100 if value else 0
        elif target == 'lets_connect':
            return 100 if LetsConnectLog.objects.filter(user=profile.user).exists() else 0
