from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Events, Participation
from .serializers import EventSerializer, ParticipationSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view
from orgs.models import Organization

@extend_schema_view(
    list=extend_schema(
        summary='List events.',
        description='This endpoint lists all events.'
    ),
    retrieve=extend_schema(
        summary='Retrieve an event.',
        description='This endpoint retrieves an event.'
    )
)
class EventViewSet(viewsets.ModelViewSet):
    queryset = Events.objects.all()
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization']

    @extend_schema(
        summary='Create an event.',
        description='This endpoint creates an event.'
    )
    def create(self, request, *args, **kwargs):
        # Check if user is a manager of the organization
        organization_id = request.data.get('organization')
        if not organization_id or not Organization.objects.filter(id=organization_id).exists():
            return Response({"detail": "The organization is blank or does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        is_manager = Organization.objects.filter(id=organization_id, managers__id=request.user.id).exists()
        if not is_manager:
            return Response({"detail": "You do not have permission to create an event for this organization."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @extend_schema(
        summary='Update an event.',
        description='This endpoint updates an event.'
    )
    def update(self, request, *args, **kwargs):
        # Check if user is a manager of the organization
        event = self.get_object()
        organization_id = event.organization.id
        is_manager = Organization.objects.filter(id=organization_id, managers__id=request.user.id).exists()
        if not is_manager:
            return Response({"detail": "You do not have permission to update this event."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "This endpoint does not support partial updates."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(
        summary='Delete an event.',
        description='This endpoint deletes an event.'
    )
    def destroy(self, request, *args, **kwargs):
        # Check if user is a manager of the organization
        event = self.get_object()
        organization_id = event.organization.id
        is_manager = Organization.objects.filter(id=organization_id, managers__id=request.user.id).exists()
        if not is_manager:
            return Response({"detail": "You do not have permission to delete this event."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class ParticipationViewSet(viewsets.ModelViewSet):
    queryset = Participation.objects.all()
    serializer_class = ParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='Create a participation.',
        description='This endpoint creates a participation.'
    )
    def create(self, request, *args, **kwargs):
        # Only the authenticated user can create a participation for themselves
        if request.data.get('user') and request.data.get('user') != request.user.id:
            return Response({"detail": "You can only create a participation for yourself."}, status=status.HTTP_403_FORBIDDEN)

        # Check if user is already participating in the event
        event_id = request.data.get('event')
        if not event_id or not Events.objects.filter(id=event_id).exists():
            return Response({"detail": "The event is blank or does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        is_participating = Participation.objects.filter(event__id=event_id, user=request.user).exists()
        if is_participating:
            return Response({"detail": "You are already participating in this event."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)