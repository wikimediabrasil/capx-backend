from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from .models import Organization, OrganizationType, TagDiff, Document, OrganizationName
from .serializers import (
    OrganizationSerializer,
    OrganizationTypeSerializer,
    TagDiffSerializer,
    DocumentSerializer,
    OrganizationNameSerializer,
)
from users.models import CustomUser as User, Territory
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from django.db import models
from django.db.models import Subquery, OuterRef
from events.models import Events

PATCH_NOT_ALLOWED_MSG = "PATCH method not allowed"

class OrganizationFilter(filters.FilterSet):
    # Backward-compatible filter: match any translation of the name
    display_name = filters.CharFilter(method='filter_display_name')

    def filter_display_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(i18n_names__name__icontains=value).distinct()

    class Meta:
        model = Organization
        fields = {
            'acronym': ['exact'],
            'type': ['exact'],
            'managers': ['exact'],
            'known_capacities': ['exact'],
            'available_capacities': ['exact'],
            'wanted_capacities': ['exact'],
            # 'display_name' is handled via method filter above
        }


@extend_schema_view(
    list=extend_schema(
        summary='List all organizations.',
        description='This endpoint lists all organizations that has been activated (i.e. has at least one manager). If the user is a staff member, all organizations are listed.',
        parameters=[
            OpenApiParameter(
                name='has_capacities_known',
                description='Filter organizations that have known capacities.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='has_capacities_available',
                description='Filter organizations that have available capacities.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='has_capacities_wanted',
                description='Filter organizations that have wanted capacities.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='has_any_capacities',
                description='Filter organizations that have any capacities.',
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name='territory',
                description='Filter organizations by territory ID.',
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name='ordering',
                description='Sort organizations by field. Prefix with "-" for descending order. Options: display_name, update_date.',
                required=False,
                type=OpenApiTypes.STR,
            ),
        ]
    ),
    retrieve=extend_schema(
        summary='Retrieve an organization by ID.',
        description='This endpoint retrieves an organization by its ID.',
    ),
    create=extend_schema(
        summary='Create a new organization.',
        description='This endpoint creates a new organization. Only staff members can create organizations.',
    ),
    destroy=extend_schema(
        summary='Delete an organization.',
        description='This endpoint deletes an organization by its ID. Only staff members can delete organizations.',
    ),
)
class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # Include display_name for backward-compatible ordering (uses English translation via annotation)
    ordering_fields = ['display_name', 'update_date']
    filterset_class = OrganizationFilter

    def get_queryset(self):
        query_params = self.request.query_params
        user = self.request.user
        # Filter organizations that have at least one manager and ensure distinct results
        queryset = Organization.objects.all() if user.is_staff else Organization.objects.filter(managers__isnull=False).distinct()
        query_filters = []

        territory_id = query_params.get('territory')
        if territory_id:
            # Include organizations in the specified territory or its child territories
            child_territory_ids = Territory.objects.filter(
                models.Q(id=territory_id) | models.Q(parent_territory__id=territory_id)
            ).values_list('id', flat=True)
            query_filters.append(models.Q(territory__id__in=child_territory_ids))

        def capacity_filter(param_name: str, capacity_field: str):
            value = query_params.get(param_name)
            if value is None:
                return None
            value_lower = value.lower()
            if value_lower == 'true':
                return models.Q(**{f"{capacity_field}__isnull": False})
            if value_lower == 'false':
                return models.Q(**{f"{capacity_field}__isnull": True})
            return None

        for param_name, capacity_field in [
            ('has_capacities_known', 'known_capacities'),
            ('has_capacities_available', 'available_capacities'),
            ('has_capacities_wanted', 'wanted_capacities'),
        ]:
            capacity_q = capacity_filter(param_name, capacity_field)
            if capacity_q:
                query_filters.append(capacity_q)

        has_any_capacities_param = query_params.get('has_any_capacities')
        if has_any_capacities_param:
            if has_any_capacities_param.lower() == 'true':
                query_filters.append(
                    models.Q(known_capacities__isnull=False) |
                    models.Q(available_capacities__isnull=False) |
                    models.Q(wanted_capacities__isnull=False)
                )
            elif has_any_capacities_param.lower() == 'false':
                query_filters.append(
                    models.Q(known_capacities__isnull=True) &
                    models.Q(available_capacities__isnull=True) &
                    models.Q(wanted_capacities__isnull=True)
                )

        if query_filters:
            combined_filter = query_filters[0]
            for extra_filter in query_filters[1:]:
                combined_filter &= extra_filter
            queryset = queryset.filter(combined_filter)

        # Annotate English name for backward-compatible ordering by display_name
        en_name_subquery = OrganizationName.objects.filter(
            organization=OuterRef('pk'), language_code='en'
        ).values('name')[:1]
        queryset = queryset.annotate(display_name=Subquery(en_name_subquery))

        return queryset.prefetch_related('i18n_names').distinct()

    def _validate_choose_events(self, organization, choose_events):
        """
        Validates the 'choose_events' field to ensure all events are associated with the given organization.
        """
        valid_events = Events.objects.filter(organization_id=organization.id if organization else None).values_list('id', flat=True)
        valid_events_set = set(valid_events)

        for event in choose_events:
            if event not in valid_events_set:
                raise ValueError(
                    f"Event with ID {event} is not associated with this organization. "
                    f"It must be in the organization's 'events' field."
                )

    @extend_schema(
        summary='Create a new organization.',
        description='This endpoint creates a new organization. Only staff members can create organizations.',
    )
    def create(self, request, *args, **kwargs):
        if request.user.is_staff is False:
            return Response("You do not have permission to create an organization.", status=status.HTTP_403_FORBIDDEN)
        if 'choose_events' in request.data:
            try:
                self._validate_choose_events(None, request.data['choose_events'])
            except ValueError as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)
        
    @extend_schema(
        summary='Updates an organization.',
        description='This endpoint updates an organization by its ID. Only staff members and managers of the organization can update it.',
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        choose_events = request.data.get('choose_events', [])

        if choose_events:
            try:
                self._validate_choose_events(instance, choose_events)
            except ValueError as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_staff or request.user in instance.managers.all():
            return super().update(request, *args, **kwargs)
        return Response("You do not have permission to update this organization.", status=status.HTTP_403_FORBIDDEN)
        
    @extend_schema(exclude=True)        
    def partial_update(self, request, *args, **kwargs):
        return Response(PATCH_NOT_ALLOWED_MSG, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(
        summary='Delete an organization.',
        description='This endpoint deletes an organization by its ID. Only staff members can delete organizations.',
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        return Response("You do not have permission to delete this organization.", status=status.HTTP_403_FORBIDDEN)


@extend_schema_view(
    list=extend_schema(
        summary='List all organization types.',
        description='This endpoint lists all organization types.',
    ),
    retrieve=extend_schema(
        summary='Retrieve an organization type by ID.',
        description='This endpoint retrieves an organization type by its ID.',
    ),
)
class OrganizationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrganizationType.objects.all()
    serializer_class = OrganizationTypeSerializer

@extend_schema_view(
    list=extend_schema(
        summary='List all tag diffs.',
        description='This endpoint lists all tag diffs.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a tag diff by ID.',
        description='This endpoint retrieves a tag diff by its ID.',
    ),
    create=extend_schema(
        summary='Create a new tag diff.',
        description='This endpoint creates a new tag diff.',
    ),
    destroy=extend_schema(
        summary='Delete a tag diff.',
        description='This endpoint deletes a tag diff by its ID.',
    ),
)
class TagDiffViewSet(viewsets.ModelViewSet):
    queryset = TagDiff.objects.all()
    serializer_class = TagDiffSerializer

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        return Response("PUT method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response(PATCH_NOT_ALLOWED_MSG, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@extend_schema_view(
    list=extend_schema(
        summary='List all documents.',
        description='This endpoint lists all documents.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a document by ID.',
        description='This endpoint retrieves a document by its ID.',
    ),
    create=extend_schema(
        summary='Create a new document.',
        description='This endpoint creates a new document.',
    ),
    destroy=extend_schema(
        summary='Delete a document.',
        description='This endpoint deletes a document by its ID.',
    ),
)
class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        return Response("PUT method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response(PATCH_NOT_ALLOWED_MSG, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@extend_schema_view(
    list=extend_schema(
        summary='List organization display name translations.',
        description='Lists all organization name translations. Filter by organization or language code.',
        parameters=[
            OpenApiParameter(
                name='organization', description='Filter by organization ID.', required=False, type=OpenApiTypes.INT
            ),
            OpenApiParameter(
                name='language_code', description='Filter by language code.', required=False, type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='ordering', description='Order by language_code or name.', required=False, type=OpenApiTypes.STR
            ),
        ]
    ),
    retrieve=extend_schema(
        summary='Retrieve a translated organization name.',
        description='Fetch a single organization name translation by ID.'
    ),
    create=extend_schema(
        summary='Create a translation for an organization name.',
        description='Create a new translation row. Staff or managers of the organization only.'
    ),
    update=extend_schema(
        summary='Update a translation for an organization name.',
        description='Update an existing translation. Staff or managers of the organization only.'
    ),
    destroy=extend_schema(
        summary='Delete a translation for an organization name.',
        description='Delete an organization name translation. Staff or managers only.'
    ),
)
class OrganizationNameViewSet(viewsets.ModelViewSet):
    queryset = OrganizationName.objects.select_related('organization').all()
    serializer_class = OrganizationNameSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization', 'language_code']
    ordering_fields = ['language_code', 'name']

    def _user_can_modify(self, user, org: Organization) -> bool:
        if user.is_staff:
            return True
        return org.managers.filter(pk=user.pk).exists()

    def create(self, request, *args, **kwargs):
        org_id = request.data.get('organization')
        if not org_id:
            return Response({'organization': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return Response({'organization': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not self._user_can_modify(request.user, org):
            return Response('You do not have permission to add a translation for this organization.', status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._user_can_modify(request.user, instance.organization):
            return Response('You do not have permission to update this translation.', status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._user_can_modify(request.user, instance.organization):
            return Response('You do not have permission to delete this translation.', status=status.HTTP_403_FORBIDDEN)
        # Stop deletion of the english translation. It can be deleted only by deleting the organization.
        if instance.language_code == 'en':
            return Response('The English translation cannot be deleted separately. Delete the organization to remove it.', status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response(PATCH_NOT_ALLOWED_MSG, status=status.HTTP_405_METHOD_NOT_ALLOWED)