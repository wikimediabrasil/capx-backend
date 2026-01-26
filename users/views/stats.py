from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from knox.models import AuthToken
from users.models import Profile, Language, LanguageProficiency
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
        total_messages = Message.objects.filter(status='sent').count()
        new_messages = Message.objects.filter(
            date__gte=last_30_days,
            status='sent'
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


class LanguagesByTerritoryView(APIView):
    """
    Pre-aggregated language counts by territory.
    Returns the number of users who speak each language, grouped by territory.
    """

    @extend_schema(
        summary='Get language user counts by territory',
        description='Returns pre-aggregated data of language speakers grouped by territory. '
                    'Each territory contains a mapping of language IDs to user counts. '
                    'Users with proficiency=0 are excluded.',
        responses={(200, 'application/json'): {
            'description': 'Language counts by territory retrieved successfully',
            'type': 'object',
            'additionalProperties': {
                'type': 'object',
                'description': 'Territory ID mapped to language counts',
                'additionalProperties': {
                    'type': 'integer',
                    'description': 'Language ID mapped to user count'
                }
            },
        }},
    )
    def get(self, request, *args, **kwargs):
        # Get all active user profiles with their territories and languages
        profiles_with_data = Profile.objects.filter(
            user__is_active=True
        ).prefetch_related(
            'territory',
            'languageproficiency_set__language'
        )

        # Aggregate data
        result = {}

        for profile in profiles_with_data:
            # Get user's territories
            territories = list(profile.territory.values_list('id', flat=True))

            # Get user's languages (excluding proficiency=0)
            languages = LanguageProficiency.objects.filter(
                profile=profile
            ).exclude(proficiency='0').values_list('language_id', flat=True)

            # For each territory, count each language
            for territory_id in territories:
                territory_key = str(territory_id)
                if territory_key not in result:
                    result[territory_key] = {}

                for language_id in languages:
                    language_key = str(language_id)
                    result[territory_key][language_key] = result[territory_key].get(language_key, 0) + 1

        return Response(result)


class CapacitiesByTerritoryView(APIView):
    """
    Pre-aggregated capacity counts by territory.
    Returns the number of users with skills available and wanted, grouped by territory.
    """

    @extend_schema(
        summary='Get capacity user counts by territory',
        description='Returns pre-aggregated data of skill/capacity counts grouped by territory. '
                    'Each territory contains a mapping of skill IDs to objects with available and wanted counts.',
        responses={(200, 'application/json'): {
            'description': 'Capacity counts by territory retrieved successfully',
            'type': 'object',
            'additionalProperties': {
                'type': 'object',
                'description': 'Territory ID mapped to capacity counts',
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'available': {'type': 'integer', 'description': 'Number of users with this skill available'},
                        'wanted': {'type': 'integer', 'description': 'Number of users who want this skill'},
                    }
                }
            },
        }},
    )
    def get(self, request, *args, **kwargs):
        # Get all active user profiles with their territories and skills
        profiles_with_data = Profile.objects.filter(
            user__is_active=True
        ).prefetch_related(
            'territory',
            'skills_available',
            'skills_wanted'
        )

        # Aggregate data
        result = {}

        for profile in profiles_with_data:
            # Get user's territories
            territories = list(profile.territory.values_list('id', flat=True))

            # Get user's skills
            skills_available = list(profile.skills_available.values_list('id', flat=True))
            skills_wanted = list(profile.skills_wanted.values_list('id', flat=True))

            # For each territory, count skills
            for territory_id in territories:
                territory_key = str(territory_id)
                if territory_key not in result:
                    result[territory_key] = {}

                # Count available skills
                for skill_id in skills_available:
                    skill_key = str(skill_id)
                    if skill_key not in result[territory_key]:
                        result[territory_key][skill_key] = {'available': 0, 'wanted': 0}
                    result[territory_key][skill_key]['available'] += 1

                # Count wanted skills
                for skill_id in skills_wanted:
                    skill_key = str(skill_id)
                    if skill_key not in result[territory_key]:
                        result[territory_key][skill_key] = {'available': 0, 'wanted': 0}
                    result[territory_key][skill_key]['wanted'] += 1

        return Response(result)
