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
        """
        Evaluate the structured JSON logic for a badge against a user's profile.
        """
        app_label = logic.get("app")
        filters = logic.get("filters", [])

        try:
            # Dynamically get the model class
            model = apps.get_model(app_label)

            # Build the query
            queryset = model.objects.all()
            for filter_item in filters:
                name = filter_item.get("name")
                lookup = filter_item.get("lookup")
                target = filter_item.get("target")

                # Resolve the target value dynamically for query expressions
                target_value = self.resolve_target_for_query(target)

                if name == "filter":
                    queryset = queryset.filter(**{lookup: target_value})
                elif name == "exists":
                    return queryset.exists()

            return False
        except Exception as e:
            self.stderr.write(f"Error evaluating logic for profile {profile.id}: {e}")
            return False

    def resolve_target_for_query(self, target):
        """
        Resolve the target string for use in Django ORM queries.
        """
        if not target:
            return None

        # Handle special cases for dynamic expressions
        if target == "now()":
            return now()
        elif target.startswith("now() - timedelta"):
            # Parse timedelta from the target string
            days = int(target.split("days=")[1].split(")")[0])
            return now() - timedelta(days=days)

        # For static values, return as-is
        return target

