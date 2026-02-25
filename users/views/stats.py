from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
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
        examples=[
            OpenApiExample(
                'Example Response',
                value={
                    "1": {"1": 10, "2": 5},
                    "2": {"1": 4, "3": 6},
                },
                description='In this example, territory 1 has 10 users who speak language 1 and 5 users who speak language 2. Territory 2 has 4 users who speak language 1 and 6 users who speak language 3.',
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        # Get counts of users who speak each language, grouped by territory, excluding proficiency=0
        aggregated_counts = (
            LanguageProficiency.objects
            .filter(
                profile__user__is_active=True,
                profile__territory__isnull=False,
            )
            .exclude(proficiency='0')
            .values('profile__territory__id', 'language_id')
            .annotate(user_count=Count('profile_id', distinct=True))
        )

        result = {}

        # Build the result structure with territory as the first level and language counts as the second level
        for row in aggregated_counts:
            territory_key = str(row['profile__territory__id'])
            language_key = str(row['language_id'])

            if territory_key not in result:
                result[territory_key] = {}

            result[territory_key][language_key] = row['user_count']

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
        examples=[
            OpenApiExample(
                'Example Response',
                value={
                    "1": {
                        "1": {"available": 10, "wanted": 5},
                        "2": {"available": 4, "wanted": 6},
                    },
                    "2": {
                        "1": {"available": 7, "wanted": 3},
                        "3": {"available": 2, "wanted": 8},
                    },
                },
                description='In this example, territory 1 has 10 users with skill 1 available and 5 users who want skill 1. It also has 4 users with skill 2 available and 6 users who want skill 2. Territory 2 has 7 users with skill 1 available and 3 users who want skill 1, as well as 2 users with skill 3 available and 8 users who want skill 3.',
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        # Get counts of users with skills available and wanted, grouped by territory and skill
        available_counts = (
            Profile.objects
            .filter(user__is_active=True, territory__isnull=False, skills_available__isnull=False)
            .values('territory__id', 'skills_available__id')
            .annotate(user_count=Count('id', distinct=True))
        )
        wanted_counts = (
            Profile.objects
            .filter(user__is_active=True, territory__isnull=False, skills_wanted__isnull=False)
            .values('territory__id', 'skills_wanted__id')
            .annotate(user_count=Count('id', distinct=True))
        )

        result = {}

        # Combine available and wanted counts into a single structure
        for row in available_counts:
            territory_key = str(row['territory__id'])
            skill_key = str(row['skills_available__id'])

            if territory_key not in result:
                result[territory_key] = {}
            if skill_key not in result[territory_key]:
                result[territory_key][skill_key] = {'available': 0, 'wanted': 0}

            result[territory_key][skill_key]['available'] = row['user_count']

        for row in wanted_counts:
            territory_key = str(row['territory__id'])
            skill_key = str(row['skills_wanted__id'])

            if territory_key not in result:
                result[territory_key] = {}
            if skill_key not in result[territory_key]:
                result[territory_key][skill_key] = {'available': 0, 'wanted': 0}

            result[territory_key][skill_key]['wanted'] = row['user_count']

        return Response(result)
