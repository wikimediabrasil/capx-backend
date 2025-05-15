from django.core.management.base import BaseCommand
from users.models import Profile, Badge, UserBadge
from django.apps import apps
from django.db.models import F, Q, Value
from django.utils.timezone import now
from datetime import timedelta

class Command(BaseCommand):
    help = "Recount metrics and attribute or promote new badges to users"

    def handle(self, *args, **kwargs):
        badges = Badge.objects.all()
        profiles = Profile.objects.all()

        for badge in badges:
            logic = badge.logic
            if not logic:
                continue

            for profile in profiles:
                if self.evaluate_logic(logic, profile):
                    UserBadge.objects.get_or_create(profile=profile, badge=badge)
                else:
                    # Remove the badge if the user no longer meets the criteria
                    UserBadge.objects.filter(profile=profile, badge=badge).delete()

    def evaluate_logic(self, logic, profile):
        
        target = logic.get('target')
        value = logic.get('value')

        if target == 'sent_messages':
            sent = Message.objects.filter(sender=profile.user).count()
            return min((sent / value) * 100, 100) if value else 0
        elif target == 'received_messages':
            received = Message.objects.filter(receiver=profile.user).count()
            return min((received / value) * 100, 100) if value else 0
        elif target == 'updated_profile':
            updated_at = profile.updated_at
            if updated_at:
                return (now() - updated_at).days <= value
            return False
        elif target == 'is_manager':
            return profile.is_manager.exists()
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
            if created_at:
                return (now() - created_at).days >= value
            return False
