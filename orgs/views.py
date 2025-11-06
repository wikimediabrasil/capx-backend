from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from .models import Organization, OrganizationType, TagDiff, Document
from .serializers import OrganizationSerializer, OrganizationTypeSerializer, TagDiffSerializer, DocumentSerializer
from users.models import CustomUser as User, Territory
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from django.db import models
from events.models import Events

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
    ordering_fields = ['display_name', 'update_date']
    filterset_fields = [
        'display_name',
        'acronym',
        'type',
        'managers',
        'known_capacities',
        'available_capacities',
        'wanted_capacities',
    ]


    def get_queryset(self):
        has_capacities_known = self.request.query_params.get('has_capacities_known', None)
        has_capacities_wanted = self.request.query_params.get('has_capacities_wanted', None)
        has_capacities_available = self.request.query_params.get('has_capacities_available', None)
        has_any_capacities = self.request.query_params.get('has_any_capacities', None)
        territory_id = self.request.query_params.get('territory')

        user = self.request.user
        if user.is_staff:
            queryset = Organization.objects.all()
        else:
            # Filter organizations that have at least one manager and ensure distinct results
            queryset = Organization.objects.filter(managers__isnull=False).distinct()
        
        if territory_id:
            # Include organizations in the specified territory or its child territories
            child_territories = Territory.objects.filter(
                models.Q(id=territory_id) | 
                models.Q(parent_territory__id=territory_id)
            ).values_list('id', flat=True)
            queryset = queryset.filter(territory__id__in=child_territories)

        if has_capacities_known is not None:
            if has_capacities_known.lower() == 'true':
                queryset = queryset.filter(known_capacities__isnull=False).distinct()
            elif has_capacities_known.lower() == 'false':
                queryset = queryset.filter(known_capacities__isnull=True).distinct()

        if has_capacities_wanted is not None:
            if has_capacities_wanted.lower() == 'true':
                queryset = queryset.filter(wanted_capacities__isnull=False).distinct()
            elif has_capacities_wanted.lower() == 'false':
                queryset = queryset.filter(wanted_capacities__isnull=True).distinct()

        if has_capacities_available is not None:
            if has_capacities_available.lower() == 'true':
                queryset = queryset.filter(available_capacities__isnull=False).distinct()
            elif has_capacities_available.lower() == 'false':
                queryset = queryset.filter(available_capacities__isnull=True).distinct()

        if has_any_capacities is not None:
            if has_any_capacities.lower() == 'true':
                queryset = queryset.filter(
                    models.Q(known_capacities__isnull=False) |
                    models.Q(available_capacities__isnull=False) |
                    models.Q(wanted_capacities__isnull=False)
                ).distinct()
            elif has_any_capacities.lower() == 'false':
                queryset = queryset.filter(
                    models.Q(known_capacities__isnull=True) &
                    models.Q(available_capacities__isnull=True) &
                    models.Q(wanted_capacities__isnull=True)
                ).distinct()

        return queryset

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
        return Response("PATCH method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)

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
        return Response("PATCH method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)

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
        return Response("PATCH method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)