from django.db import models
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes
from users.models import Profile
from users.submodels import Territory
from users.serializers import ProfileSerializer



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
            OpenApiParameter(
                name='ordering',
                description='Sort users by field. Prefix with "-" for descending order. Options: last_update.',
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
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['last_update']
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
            # Fuzzy search: case-insensitive partial match on username or profile wiki_alt
            queryset = queryset.filter(
                models.Q(user__username__icontains=name_search) |
                models.Q(wiki_alt__icontains=name_search)
            ).distinct()

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



