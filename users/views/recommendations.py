from django.db import models
from django.db.models import Count, F
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from users.models import Profile, SavedItem
from users.serializers import (
    RecommendationUserSerializer,
    RecommendationOrganizationSerializer,
)
from orgs.models import Organization
from events.models import Events
from skills.models import Skill


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get personalized recommendations for the logged-in user.',
        description='Returns people to share skills with or learn from, people with the same language(s), organizations to share with or learn from, new skills to consider, and upcoming events related to user skills.',
        parameters=[
            OpenApiParameter(
                name='limit',
                description='Maximum number of items per list (default 10, max 50).',
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name='ignore_saved',
                description='When true, ignore users and organizations the requester has saved (default: true).',
                required=False,
                type=OpenApiTypes.BOOL,
                default=True,
            ),
        ],
        responses={(200, 'application/json'): {
            'type': 'object',
            'properties': {
                'share_with': {'type': 'array', 'items': {'type': 'object'}},
                'learn_from': {'type': 'array', 'items': {'type': 'object'}},
                'same_language': {'type': 'array', 'items': {'type': 'object'}},
                'share_with_orgs': {'type': 'array', 'items': {'type': 'object'}},
                'learn_from_orgs': {'type': 'array', 'items': {'type': 'object'}},
                'new_skills': {'type': 'array', 'items': {'type': 'object'}},
                'events': {'type': 'array', 'items': {'type': 'object'}},
            }
        }}
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return Response({
                'share_with': [],
                'learn_from': [],
                'same_language': [],
                'share_with_orgs': [],
                'learn_from_orgs': [],
                'new_skills': [],
                'events': [],
            })

        # Results limit
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            limit = 10
        limit = max(1, min(limit, 50))

        # Whether to ignore already-saved users/orgs (default True)
        ignore_saved_param = str(request.query_params.get('ignore_saved', 'true')).lower()
        ignore_saved = ignore_saved_param not in ('false', '0', 'no')

        saved_user_ids = []
        saved_org_ids = []
        if ignore_saved:
            saved_user_ids = list(
                SavedItem.objects.filter(user=user, entity='user')
                .values_list('related_user_id', flat=True)
            )
            saved_org_ids = list(
                SavedItem.objects.filter(user=user, entity='org')
                .values_list('related_org_id', flat=True)
            )

        # Collect user's skills
        skills_known_ids = set(profile.skills_known.values_list('id', flat=True))
        skills_available_ids = set(profile.skills_available.values_list('id', flat=True))
        skills_wanted_ids = set(profile.skills_wanted.values_list('id', flat=True))
        all_user_skill_ids = skills_known_ids | skills_available_ids | skills_wanted_ids

        # People to share skills with: others who want what I can teach
        share_with_qs = (
            Profile.objects.exclude(pk=profile.pk)
            .exclude(user__id__in=saved_user_ids)
            .annotate(
                match_count=Count(
                    'skills_wanted',
                    filter=models.Q(skills_wanted__id__in=list(skills_available_ids)),
                    distinct=True,
                )
            )
            .filter(match_count__gt=0)
            .order_by('-match_count', '?')[:limit]
        )

        # People to learn from: others who can teach what I want
        learn_from_qs = (
            Profile.objects.exclude(pk=profile.pk)
            .exclude(user__id__in=saved_user_ids)
            .annotate(
                match_count=Count(
                    'skills_available',
                    filter=models.Q(skills_available__id__in=list(skills_wanted_ids)),
                    distinct=True,
                )
            )
            .filter(match_count__gt=0)
            .order_by('-match_count', '?')[:limit]
        )

        # Same language people: rank by number of shared languages (exclude proficiency 0), randomize ties
        lang_ids = list(
            profile.languageproficiency_set.exclude(proficiency=0).values_list('language_id', flat=True)
        )
        same_lang_qs = (
            Profile.objects.exclude(pk=profile.pk)
            .exclude(user__id__in=saved_user_ids)
            .annotate(
                match_count=Count(
                    'languageproficiency',
                    filter=(
                        models.Q(languageproficiency__language_id__in=lang_ids)
                        & ~models.Q(languageproficiency__proficiency=0)
                    ),
                    distinct=True,
                )
            )
            .filter(match_count__gt=0)
            .order_by('-match_count', '?')[:limit]
        )

        # New skills: popular skills the user doesn't have/want yet
        new_skills_qs = (
            Skill.objects.exclude(id__in=list(all_user_skill_ids))
            .annotate(
                known_count=Count('user_known_skills', distinct=True),
                available_count=Count('user_available_skills', distinct=True),
            )
            .annotate(popularity=F('known_count') + F('available_count'))
            .order_by('-popularity', '?')[:limit]
        )

        # Events: upcoming events related to my skills
        now = timezone.now()
        related_ids = list(skills_known_ids | skills_wanted_ids)
        events_qs = (
            Events.objects.filter(
                related_skills__id__in=related_ids,
                time_begin__gte=now
            ).order_by('time_begin').distinct()[:limit]
        )

        # Organizations to share skills with: organizations that want what I can teach
        share_with_orgs_qs = (
            Organization.objects.filter(managers__isnull=False)
            .exclude(id__in=saved_org_ids)
            .annotate(
                match_count=Count(
                    'wanted_capacities',
                    filter=models.Q(wanted_capacities__id__in=list(skills_available_ids)),
                    distinct=True,
                )
            )
            .filter(match_count__gt=0)
            .order_by('-match_count', '?')[:limit]
        )

        # Organizations to learn from: organizations that can teach what I want
        learn_from_orgs_qs = (
            Organization.objects.filter(managers__isnull=False)
            .exclude(id__in=saved_org_ids)
            .annotate(
                match_count=Count(
                    'available_capacities',
                    filter=models.Q(available_capacities__id__in=list(skills_wanted_ids)),
                    distinct=True,
                )
            )
            .filter(match_count__gt=0)
            .order_by('-match_count', '?')[:limit]
        )

        # Serialize
        from skills.serializers import SkillSerializer  # local import to avoid cycles
        from events.serializers import EventSerializer

        data = {
            'share_with': RecommendationUserSerializer(share_with_qs, many=True).data,
            'learn_from': RecommendationUserSerializer(learn_from_qs, many=True).data,
            'same_language': RecommendationUserSerializer(same_lang_qs, many=True).data,
            'share_with_orgs': RecommendationOrganizationSerializer(share_with_orgs_qs, many=True).data,
            'learn_from_orgs': RecommendationOrganizationSerializer(learn_from_orgs_qs, many=True).data,
            'new_skills': SkillSerializer(new_skills_qs, many=True).data,
            'events': EventSerializer(events_qs, many=True).data,
        }

        return Response(data)