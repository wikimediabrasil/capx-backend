from datetime import timedelta
from django.utils import timezone
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from knox.models import AuthToken
from users.models import Profile, Language
from skills.models import Skill
from users.models import Territory
from message.models import Message
from orgs.models import Organization


class StatisticsView(APIView):

    @extend_schema(
        summary='Get statistics about users, capacities, messages, and organizations.',
        description='This endpoint retrieves statistics about users, capacities, messages, and organizations.',
        responses={(200, 'application/json'): {
            'description': 'Statistics retrieved successfully',
            'type': 'object',
            'properties': {
                'total_users': {'type': 'integer', 'description': 'Total number of users'},
                'new_users': {'type': 'integer', 'description': 'Number of new users this month'},
                'active_users': {'type': 'integer', 'description': 'Number of active users in the last 30 days'},
                'total_capacities': {'type': 'integer', 'description': 'Total number of capacities'},
                'new_capacities': {'type': 'integer', 'description': 'Number of new capacities this month'},
                'total_messages': {'type': 'integer', 'description': 'Total number of messages'},
                'new_messages': {'type': 'integer', 'description': 'Number of new messages this month'},
                'total_organizations': {'type': 'integer', 'description': 'Total number of active organizations'},
                'new_organizations': {'type': 'integer', 'description': 'Number of organizations activated this month'},
                'territory_user_counts': {
                    'type': 'object',
                    'description': 'Mapping of root territory IDs to the number of users in each territory (including child territories)',
                    'additionalProperties': {'type': 'integer'},
                },
                'language_user_counts': {
                    'type': 'object',
                    'description': 'Mapping of language IDs to the number of users who speak each language',
                    'additionalProperties': {'type': 'integer'},
                },
                'skill_known_user_counts': {
                    'type': 'object',
                    'description': 'Mapping of root skill IDs to the number of users who know each skill (including child skills)',
                    'additionalProperties': {'type': 'integer'},
                },
                'skill_available_user_counts': {
                    'type': 'object',
                    'description': 'Mapping of root skill IDs to the number of users who have each skill available (including child skills)',
                    'additionalProperties': {'type': 'integer'},
                },
                'skill_wanted_user_counts': {
                    'type': 'object',
                    'description': 'Mapping of root skill IDs to the number of users who want each skill (including child skills)',
                    'additionalProperties': {'type': 'integer'},
                },
            },
        }},
    )
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        
        # Calculate total users and percentage change
        total_users = Profile.objects.filter(user__is_active=True).count()
        new_users = Profile.objects.filter(
            user__date_joined__gte=last_30_days,
            user__is_active=True
        ).count()
        recent_user_ids = AuthToken.objects.filter(created__gte=last_30_days).values_list('user_id', flat=True).distinct()
        active_users = Profile.objects.filter(user__id__in=recent_user_ids, user__is_active=True).count()

        # Calculate total capacities and new capacities this month
        total_capacities = Skill.objects.count()
        new_capacities = Skill.objects.filter(
            skill_date_of_creation__gte=last_30_days
        ).count()

        # Calculate total messages and new messages this month
        total_messages = Message.objects.count()
        new_messages = Message.objects.filter(
            date__gte=last_30_days
        ).count()

        # Calculate total of organizations with managers and within this month
        total_organizations = Organization.objects.filter(managers__isnull=False).distinct().count()
        new_organizations = Organization.objects.filter(
            managers__isnull=False,
            management__joined_at__gte=last_30_days
        ).distinct().count()

        # Filter root territories and count users in each, including child territories
        root_territories = Territory.objects.filter(parent_territory__isnull=True)
        territory_user_counts = {}
        for territory in root_territories:
            child_ids = Territory.objects.filter(
                models.Q(id=territory.id) | models.Q(parent_territory=territory)
            ).values_list('id', flat=True)
            territory_user_counts[territory.id] = Profile.objects.filter(
                user__is_active=True,
                territory__id__in=child_ids
            ).values('user_id').distinct().count()

        # Count users by language, ignore when proficiency is 0 but include when proficiency is null
        languages = Language.objects.all()
        language_user_counts = {}
        for language in languages:
            language_user_counts[language.id] = Profile.objects.filter(
                user__is_active=True,
                languageproficiency__language=language
            ).exclude(languageproficiency__proficiency=0).values('user_id').distinct().count()

        # Count users by root skills
        root_skills = Skill.objects.filter(skill_type__isnull=True)
        skill_known_user_counts = {}
        skill_available_user_counts = {}
        skill_wanted_user_counts = {}
        def get_all_descendant_skill_ids(skill):
            descendants = set()
            children = Skill.objects.filter(skill_type=skill)
            for child in children:
                descendants.add(child.id)
                descendants.update(get_all_descendant_skill_ids(child))
            return descendants

        for skill in root_skills:
            # Get all descendant skill IDs recursively, including the root skill itself
            all_skill_ids = {skill.id}
            all_skill_ids.update(get_all_descendant_skill_ids(skill))

            skill_known_user_counts[skill.id] = Profile.objects.filter(
                user__is_active=True,
                skills_known__id__in=all_skill_ids
            ).values('user_id').distinct().count()
            skill_available_user_counts[skill.id] = Profile.objects.filter(
                user__is_active=True,
                skills_available__id__in=all_skill_ids
            ).values('user_id').distinct().count()
            skill_wanted_user_counts[skill.id] = Profile.objects.filter(
                user__is_active=True,
                skills_wanted__id__in=all_skill_ids
            ).values('user_id').distinct().count()

        return Response({
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "total_capacities": total_capacities,
            "new_capacities": new_capacities,
            "total_messages": total_messages,
            "new_messages": new_messages,
            "total_organizations": total_organizations,
            "new_organizations": new_organizations,
            "territory_user_counts": territory_user_counts,
            "language_user_counts": language_user_counts,
            "skill_known_user_counts": skill_known_user_counts,
            "skill_available_user_counts": skill_available_user_counts,
            "skill_wanted_user_counts": skill_wanted_user_counts,
        })
