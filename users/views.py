from .models import Profile, Territory, Language, WikimediaProject, Avatar, SavedItem, Badge, UserBadge
from orgs.models import Organization
from .serializers import ProfileSerializer, TerritorySerializer, LanguageSerializer, WikimediaProjectSerializer, UsersBySkillSerializer, UsersByTagSerializer, AvatarSerializer, SavedItemSerializer, BadgeSerializer, UserBadgeSerializer, RecommendationUserSerializer
from skills.models import Skill
from events.models import Events
from projects.models import Project
from message.models import Message
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiExample, OpenApiResponse
from rest_framework.views import APIView
from datetime import datetime
from django.utils import timezone
from datetime import timedelta
from knox.models import AuthToken
from django.db.models import Count, F


@extend_schema_view(
    list=extend_schema(
        summary='List all users.',
        description='This endpoint lists all users.',
        parameters=[
            OpenApiParameter(
                name='has_skills_known',
                description='Filter users by whether they have known skills.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='has_skills_available',
                description='Filter users by whether they have available skills.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='has_skills_wanted',
                description='Filter users by whether they have wanted skills.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='has_any_skills',
                description='Filter users by whether they have any skills.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='territory',
                description='Filter users by territory ID.',
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name='name',
                description='Fuzzy search for users by username. Case-insensitive partial matching.',
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary='Retrieve a user by ID.',
        description='This endpoint retrieves a user by their ID.',
    ),
)
class UsersViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'user__username',
        'about',
        'wikimedia_project',
        'affiliation',
        'languageproficiency__language',
        'skills_known',
        'skills_available',
        'skills_wanted'
    ]


    def get_queryset(self):
        queryset = super().get_queryset()
        has_skills_known = self.request.query_params.get('has_skills_known')
        has_skills_available = self.request.query_params.get('has_skills_available')
        has_skills_wanted = self.request.query_params.get('has_skills_wanted')
        has_any_skills = self.request.query_params.get('has_any_skills')
        territory_id = self.request.query_params.get('territory')
        name_search = self.request.query_params.get('name')

        if territory_id:
            # Include profiles in the specified territory or its child territories
            child_territories = Territory.objects.filter(
                models.Q(id=territory_id) | 
                models.Q(parent_territory__id=territory_id)
            ).values_list('id', flat=True)
            queryset = queryset.filter(territory__id__in=child_territories)

        if name_search and name_search.strip():
            # Fuzzy search: case-insensitive partial match on username
            queryset = queryset.filter(user__username__icontains=name_search)

        if has_skills_known is not None:
            if has_skills_known.lower() == 'true':
                queryset = queryset.filter(skills_known__isnull=False).distinct()
            elif has_skills_known.lower() == 'false':
                queryset = queryset.filter(skills_known__isnull=True).distinct()

        if has_skills_available is not None:
            if has_skills_available.lower() == 'true':
                queryset = queryset.filter(skills_available__isnull=False).distinct()
            elif has_skills_available.lower() == 'false':
                queryset = queryset.filter(skills_available__isnull=True).distinct()

        if has_skills_wanted is not None:
            if has_skills_wanted.lower() == 'true':
                queryset = queryset.filter(skills_wanted__isnull=False).distinct()
            elif has_skills_wanted.lower() == 'false':
                queryset = queryset.filter(skills_wanted__isnull=True).distinct()

        if has_any_skills is not None:
            if has_any_skills.lower() == 'true':
                queryset = queryset.filter(
                    models.Q(skills_known__isnull=False) |
                    models.Q(skills_available__isnull=False) |
                    models.Q(skills_wanted__isnull=False)
                ).distinct()
            elif has_any_skills.lower() == 'false':
                queryset = queryset.filter(
                    models.Q(skills_known__isnull=True) &
                    models.Q(skills_available__isnull=True) &
                    models.Q(skills_wanted__isnull=True)
                ).distinct()

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary='List the profile of the logged-in user.',
        description='This endpoint lists the profile of the logged-in user.',
    ),
    retrieve=extend_schema(
        summary='Retrieve the profile of the logged-in user.',
        description='This endpoint retrieves the profile of the logged-in user.',
    ),
)
class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'head', 'delete', 'options']

    def get_queryset(self):
        # Only allow the logged-in user to access their own profile
        return Profile.objects.filter(user=self.request.user)


    @extend_schema(
        summary='Update the profile of the logged-in user.',
        description='This endpoint updates the profile of the logged-in user.',
        parameters=[
            ProfileSerializer,
            OpenApiParameter(
                name='user',
                required=False,
                description='Object containing the user data.',
                type={
                    'type': 'object', 
                    'properties': {
                        'email': {'type': 'string', 'format': 'email'},
                    },
                },
            ),
            OpenApiParameter(
                name='contact',
                required=False,
                description='Object containing the contact data.',
                type={
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'display_name': {'type': 'string'},
                            'value': {'type': 'string'},
                        },
                    },
                },
            ),
            OpenApiParameter(
                name='social',
                required=False,
                description='Object containing the social media data.',
                type={
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'display_name': {'type': 'string'},
                            'value': {'type': 'string'},
                        },
                    },
                },
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the requesting user is the owner of the profile
        if instance.user == request.user:

            # Verify if there are any mismatch between skill_known and skill_available
            no_value = object()

            if request.data.get('skills_known', no_value) is no_value:
                skills_known = set(map(str, instance.skills_known.all().values_list('id', flat=True)))
            else:
                skills_known = set(request.data.get('skills_known'))

            if request.data.get('skills_available', no_value) is no_value:
                skills_available = set(map(str, instance.skills_available.all().values_list('id', flat=True)))
            else:    
                skills_available = set(request.data.get('skills_available'))

            if skills_available - skills_known:
                response = {'message': 'You cannot add a skill to skills_available that is not in skills_known.'}
                return Response(response, status=status.HTTP_409_CONFLICT)
            
            # Establish limits for the number of territories, languages, and affiliations
            max_languages = 20
            max_territories = 10
            max_affiliations = 10

            territories = len(request.data.get('territory', []) or [])
            languages = len(request.data.get('language', {}) or {})
            affiliations = len(request.data.get('affiliation', []) or [])

            if territories > max_territories:
                response = {'message': f'You cannot add more than {max_territories} territories.'}
                return Response(response, status=status.HTTP_409_CONFLICT)
            if languages > max_languages:
                response = {'message': f'You cannot add more than {max_languages} languages.'}
                return Response(response, status=status.HTTP_409_CONFLICT)
            if affiliations > max_affiliations:
                response = {'message': f'You cannot add more than {max_affiliations} affiliations.'}
                return Response(response, status=status.HTTP_409_CONFLICT)

            # Temporarily prevents automated_lets_connect from being set to False once it's True
            # TODO: Remove this once lets connect integration is complete
            if instance.automated_lets_connect and not request.data.get('automated_lets_connect', True):
                response = {'message': 'automated_lets_connect cannot be set to False once it has been True.'}
                return Response(response, status=status.HTTP_409_CONFLICT)

            # If all checks pass, proceed with the update
            return super().update(request, *args, **kwargs)


    @extend_schema(
        summary='Delete the profile of the logged-in user.',
        description='This endpoint deletes the profile of the logged-in user.',
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user == request.user:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        # Delete the associated CustomUser when a Profile is deleted
        user = instance.user
        instance.delete()
        user.delete()

@extend_schema_view(
    list=extend_schema(
        summary='List all Wikimedia projects.',
        description='This endpoint lists all Wikimedia projects.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a Wikimedia project by ID.',
        description='This endpoint retrieves a Wikimedia project by its ID.',
    ),
)
class WikimediaProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WikimediaProject.objects.all()
    serializer_class = WikimediaProjectSerializer

@extend_schema_view(
    list=extend_schema(
        summary='List all territories.',
        description='This endpoint lists all territories.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a territory by ID.',
        description='This endpoint retrieves a territory by its ID.',
    ),
)
class TerritoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Territory.objects.all()
    serializer_class = TerritorySerializer

@extend_schema_view(
    list=extend_schema(
        summary='List all avatars.',
        description='This endpoint lists all avatars.',
    ),
    retrieve=extend_schema(
        summary='Retrieve an avatar by ID.',
        description='This endpoint retrieves an avatar by its ID.',
    ),
)
class AvatarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Avatar.objects.all()
    serializer_class = AvatarSerializer


class UsersBySkillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = UsersBySkillSerializer

    @extend_schema(
        summary='List users by skill.',
        description='Deprecated. This endpoint lists users by skill. Please use the /tags/ endpoint instead.',
        deprecated=True
    )
    def retrieve(self, request, *args, **kwargs):
        skill_id = self.kwargs['pk']
        skill = get_object_or_404(Skill, pk=skill_id)

        known_users = Profile.objects.filter(skills_known=skill)
        available_users = Profile.objects.filter(skills_available=skill)
        wanted_users = Profile.objects.filter(skills_wanted=skill)
        data = {
            'known': [{'id': user.id, 'display_name': user.display_name, 'username': user.user.username, 'profile_image': user.profile_image} for user in known_users],
            'available': [{'id': user.id, 'display_name': user.display_name, 'username': user.user.username, 'profile_image': user.profile_image} for user in available_users],
            'wanted': [{'id': user.id, 'display_name': user.display_name, 'username': user.user.username, 'profile_image': user.profile_image} for user in wanted_users],
        }
        return Response(data)

    @extend_schema(exclude=True)
    def list(self, request, *args, **kwargs):
        response = {'message': 'Please provide a skill id.'}
        return Response(response, status=status.HTTP_400_BAD_REQUEST)


class QuickListViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_url_kwarg = 'list_type'

    def get_queryset(self):
        list_type = self.kwargs.get('list_type')
        if list_type == 'language':
            return Language.objects.all()
        elif list_type == 'wikimedia_project':
            return WikimediaProject.objects.all()
        elif list_type == 'affiliation':
            return Organization.objects.all()
        elif list_type == 'territory':
            return Territory.objects.all()
        elif list_type == 'event':
            return Events.objects.all()
        elif list_type == 'project':
            return Project.objects.all()
        elif list_type == 'skills':
            return Skill.objects.all()
        elif list_type == 'badges':
            return Badge.objects.all()
        elif list_type == 'users':
            return Profile.objects.all()
        else:
            # Dummy empty queryset to avoid errors in the schema generation
            return Profile.objects.none()
    
    def get_serializer_class(self): # pragma: no cover
        # Dummy method to avoid errors in the schema generation
        return ProfileSerializer

    @extend_schema(
        summary='List all items in a simplified way.',
        description='This endpoint lists all items of a given type in a simplified way.',
        parameters=[
            OpenApiParameter(
                "list_type",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                required=True,
                description='The type of list to retrieve.',
                enum=['language', 'wikimedia_project', 'affiliation', 'territory', 'skills', 'event', 'project', 'badges', 'users'],
            ),
        ],
        responses={(200, 'application/json'): {
            'description': 'A mapping of item IDs to item names.',
            'type': 'object',
            'additionalProperties': {
                'type': 'string',
            },
            'example': {
                '1': 'Label 1',
                '2': 'Label 2',
                '3': 'Label 3',
            },
        }},
    )
    def retrieve(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = {item.id: str(item) for item in queryset}
        return Response(data)

    @extend_schema(
        exclude=True
    )
    def list(self, request, *args, **kwargs):
        return Response({'message': 'Please provide a valid list type.'}, status=status.HTTP_400_BAD_REQUEST)


class UsersByTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = UsersByTagSerializer

    @extend_schema(
        summary='Lists users by tag.',
        description='This endpoint retrieves users by tag.',
        parameters=[
            OpenApiParameter(
                "tag_type",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                required=True,
                description='The type of tag to search for.',
                enum=['skill_known', 'skill_available', 'skill_wanted', 'language', 'territory', 'wikimedia_project', 'affiliation'],
            ),
            OpenApiParameter(
                "tag_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
                required=True,
                description='The ID of the tag to search for.',
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        tag_type = kwargs.get('tag_type')
        tag_id = kwargs.get('tag_id')
        if not tag_type or not tag_id:
            return Response({'message': 'Please provide a valid tag type and tag ID.'}, status=status.HTTP_400_BAD_REQUEST)

        if tag_type == 'skill_known':
            queryset = Profile.objects.filter(skills_known__id=tag_id)
        elif tag_type == 'skill_available':
            queryset = Profile.objects.filter(skills_available__id=tag_id)
        elif tag_type == 'skill_wanted':
            queryset = Profile.objects.filter(skills_wanted__id=tag_id)
        elif tag_type == 'language':
            queryset = Profile.objects.filter(languageproficiency__language__id=tag_id)
        elif tag_type == 'territory':
            queryset = Profile.objects.filter(territory__id=tag_id)
        elif tag_type == 'wikimedia_project':
            queryset = Profile.objects.filter(wikimedia_project__id=tag_id)
        elif tag_type == 'affiliation':
            queryset = Profile.objects.filter(affiliation__id=tag_id)
        else:
            return Response({'message': 'Invalid tag type. Options are: skill_known, skill_available, skill_wanted, language, territory, wikimedia_project, affiliation.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(queryset, many=True).data)

@extend_schema_view(
    list=extend_schema(
        summary='List all items saved by the logged-in user.',
        description='This endpoint lists all items saved by the logged-in user.',
    ),
    create=extend_schema(
        summary='Create a new saved item.',
        description='This endpoint creates a new saved item.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a saved item by ID.',
        description='This endpoint retrieves a saved item by its ID.',
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
                required=True,
                description='The ID of the saved item to retrieve.',
            ),
        ],
    ),
    destroy=extend_schema(
        summary='Delete a saved item by ID.',
        description='This endpoint deletes a saved item by its ID.',
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
                required=True,
                description='The ID of the saved item to retrieve.',
            ),
        ],
    ),
)
class SavedItemViewSet(viewsets.ModelViewSet):
    serializer_class = SavedItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedItem.objects.filter(user=self.request.user).exclude(related_user__is_active=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        relation = request.data.get('relation')
        entity = request.data.get('entity')
        entity_id = request.data.get('entity_id')

        if entity == 'org':
            existing_item = SavedItem.objects.filter(
                user=user, relation=relation, entity='org', related_org_id=entity_id
            ).first()
        elif entity == 'user':
            existing_item = SavedItem.objects.filter(
                user=user, relation=relation, entity='user', related_user_id=entity_id
            ).first()
        else:
            return Response({'message': 'Invalid entity type.'}, status=status.HTTP_400_BAD_REQUEST)

        if existing_item:
            serializer = self.get_serializer(existing_item)
            return Response(serializer.data, status=status.HTTP_208_ALREADY_REPORTED)

        return super().create(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        response = {'message': 'Partial updates are not allowed for saved items.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        response = {'message': 'Updates are not allowed for saved items.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@extend_schema_view(
    list=extend_schema(
        summary='List all badges.',
        description='This endpoint lists all badges.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a badge by ID.',
        description='This endpoint retrieves a badge by its ID.',
    ),
)
class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer


@extend_schema_view(
    list=extend_schema(
        summary='List all user badges.',
        description='This endpoint lists all user badges.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a user badge by ID.',
        description='This endpoint retrieves a user badge by its ID.',
    ),
    update=extend_schema(
        summary='Update a user badge.',
        description='This endpoint updates a user badge.',
    ),
)
class UserBadgeViewSet(viewsets.ModelViewSet):
    queryset = UserBadge.objects.all()
    serializer_class = UserBadgeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user == request.user:
            return super().update(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def create(self, request, *args, **kwargs):
        return Response({'message': 'Creating user badges is not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Deleting user badges is not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Partial updates are not allowed for user badges.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


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


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get personalized recommendations for the logged-in user.',
        description='Returns people to share skills with or learn from, people with the same language(s), new skills to consider, and upcoming events related to user skills.',
        parameters=[
            OpenApiParameter(
                name='limit',
                description='Maximum number of items per list (default 10, max 50).',
                required=False,
                type=OpenApiTypes.INT,
            ),
        ],
        responses={(200, 'application/json'): {
            'type': 'object',
            'properties': {
                'share_with': {'type': 'array', 'items': {'type': 'object'}},
                'learn_from': {'type': 'array', 'items': {'type': 'object'}},
                'same_language': {'type': 'array', 'items': {'type': 'object'}},
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
                'new_skills': [],
                'events': [],
            })

        # Results limit
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            limit = 10
        limit = max(1, min(limit, 50))

        # Collect user's skills
        skills_known_ids = set(profile.skills_known.values_list('id', flat=True))
        skills_available_ids = set(profile.skills_available.values_list('id', flat=True))
        skills_wanted_ids = set(profile.skills_wanted.values_list('id', flat=True))
        all_user_skill_ids = skills_known_ids | skills_available_ids | skills_wanted_ids

        # People to share skills with: others who want what I can teach
        share_with_qs = (
            Profile.objects.exclude(pk=profile.pk)
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

        # Serialize
        from skills.serializers import SkillSerializer  # local import to avoid cycles
        from events.serializers import EventSerializer

        data = {
            'share_with': RecommendationUserSerializer(share_with_qs, many=True).data,
            'learn_from': RecommendationUserSerializer(learn_from_qs, many=True).data,
            'same_language': RecommendationUserSerializer(same_lang_qs, many=True).data,
            'new_skills': SkillSerializer(new_skills_qs, many=True).data,
            'events': EventSerializer(events_qs, many=True).data,
        }

        return Response(data)