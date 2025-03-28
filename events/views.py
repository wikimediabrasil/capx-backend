from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from .models import Events, EventParticipant, EventOrganizations
from .serializers import EventSerializer, EventParticipantSerializer, EventOrganizationsSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(
        summary='List events.',
        description='This endpoint lists all events.'
    ),
    retrieve=extend_schema(
        summary='Retrieve an event.',
        description='This endpoint retrieves an event.'
    ),
    create=extend_schema(
        summary='Create an event.',
        description='This endpoint creates an event.'
    )
)
class EventViewSet(viewsets.ModelViewSet):
    queryset = Events.objects.all()
    serializer_class = EventSerializer

    @extend_schema(
        summary='Update an event.',
        description='This endpoint updates an event. Only the organizer or staff can update an event.'
    )
    def update(self, request, *args, **kwargs):
        team = EventParticipant.objects.filter(event=self.get_object(), role__in=['organizer', 'committee'])
        if request.user.pk in team.values_list('participant', flat=True) or request.user.is_staff:
            return super().update(request, *args, **kwargs)
        else:
            return Response("Only the organizer or staff can edit this event", status=status.HTTP_403_FORBIDDEN)
        
    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response("PATCH method is not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
        # Automatically enroll the creator as an organizer
        EventParticipant.objects.create(
            event=serializer.instance, 
            participant=self.request.user, 
            role='organizer',
            confirmed_organizer=True,
            confirmed_participant=True
        )
    
    @extend_schema(
        summary='Delete an event.',
        description='This endpoint deletes an event. Only staff can delete an event.'
    )
    def destroy(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        else:
            return Response("Only staff can delete an event", status=status.HTTP_403_FORBIDDEN)

@extend_schema_view(
    list=extend_schema(
        summary='List event participants.',
        description='This endpoint lists all event participants.'
    ),
)
class EventParticipantViewSet(viewsets.ModelViewSet):
    queryset = EventParticipant.objects.all()
    serializer_class = EventParticipantSerializer
    
    # On retrieve, only the field confirmed_organizer and confirmed_participant are editable
    @extend_schema(
        summary='Retrieve an event participant.',
        description='This endpoint retrieves an event participant.',
    )
    def retrieve(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().retrieve(request, *args, **kwargs)
        else:
            self.serializer_class.Meta.read_only_fields += ['event', 'participant', 'role']
        
        if request.user != self.get_object().participant:
            self.serializer_class.Meta.read_only_fields += ['confirmed_participant']

        team = EventParticipant.objects.filter(event=self.get_object().event, role__in=['organizer', 'committee'])
        if request.user.pk not in team.values_list('participant', flat=True):
            self.serializer_class.Meta.read_only_fields += ['confirmed_organizer']

        return super().retrieve(request, *args, **kwargs)
        
    @extend_schema(
        summary='Create an event participant.',
        description='This endpoint creates an event participant. Only the organizer, committee or staff can create a participant.'
    )
    def create(self, request, *args, **kwargs):
        team = EventParticipant.objects.filter(event=request.data['event'], role__in=['organizer', 'committee'])
        if (
            request.user.pk in team.values_list('participant', flat=True) or 
            request.user.is_staff
        ):
            # Confirmed_organizer are true and confirmed_participant are false by default
            data = request.data.copy()
            data['confirmed_organizer'] = True
            data['confirmed_participant'] = False
            request._full_data = data
            return super().create(request, *args, **kwargs)
        else:
            return Response("Only the organizer, committee or staff can create a participant", status=status.HTTP_403_FORBIDDEN)
        
    # Other users on the team cannot unconfirm a user if the user is the creator of the event
    @extend_schema(
        summary='Update an event participant.',
        description='This endpoint updates an event participant. ' +
            'Only the participant can confirm or unconfirm themselves, ' +
            'the organizer, committee or staff can edit participants and ' +
            'the creator of the event cannot be unconfirmed.'
    )
    def update(self, request, *args, **kwargs):
        team = EventParticipant.objects.filter(event=request.data['event'], role__in=['organizer', 'committee'])

        # Create a map of the fields of the request data and the self object
        # and check which fields have changed
        obj = self.get_object()
        fields = {f.name: getattr(obj, f.name) for f in obj._meta.fields}
        changed_fields = [
            field for field in request.data.keys() 
            if 
                field in fields and 
                str(request.data[field]) != str(
                    fields[field].id if hasattr(fields[field], 'id') else fields[field]
                )
        ]

        # Check if user is not staff
        if request.user.is_staff:
            return super().update(request, *args, **kwargs)

        # Check if user is not in the team
        if (request.user.pk not in team.values_list('participant', flat=True)):            
            # Check if more than one field changed and confirmed_participant is not one of them
            if request.user.pk != self.get_object().participant.pk or ( 
                len(changed_fields) > 1 and 'confirmed_participant' not in changed_fields
            ):
                return Response("Only the organizer, committee or staff can edit participants", status=status.HTTP_403_FORBIDDEN)
        
        # Check if the user is trying to unconfirm the creator of the event
        if self.get_object().participant == self.get_object().event.creator:
            if 'confirmed_organizer' in changed_fields:
                return Response("The creator of the event cannot be unconfirmed", status=status.HTTP_403_FORBIDDEN)
            
        # Check if the user is trying to modify the confirmed_participant field and is not the participant
        if 'confirmed_participant' in changed_fields and request.user.pk != self.get_object().participant.pk:
            return Response("Only the participant can confirm or unconfirm themselves", status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response("PATCH method is not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(
        summary='Delete an event participant.',
        description='This endpoint deletes an event participant. Only staff can delete an event participant.'
    )
    def destroy(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        else:
            return Response("Only staff can delete an event participant", status=status.HTTP_403_FORBIDDEN)

@extend_schema_view(
    list=extend_schema(
        summary='List event organizations.',
        description='This endpoint lists all event organizations.'
    ),
)
class EventOrganizationsViewSet(viewsets.ModelViewSet):
    queryset = EventOrganizations.objects.all()
    serializer_class = EventOrganizationsSerializer
    
    # On retrieve, only the field confirmed_organizer and confirmed_organization are editable
    @extend_schema(
        summary='Retrieve an event organization.',
        description='This endpoint retrieves an event organization.',
    )
    def retrieve(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().retrieve(request, *args, **kwargs)
        else:
            self.serializer_class.Meta.read_only_fields += ['event', 'organization', 'role']

        # Only managers of the organization can confirm the organization
        if request.user.pk not in self.get_object().organization.managers.values_list('pk', flat=True):
            self.serializer_class.Meta.read_only_fields += ['confirmed_organization']
        
        event_id = self.get_object().event.id
        team = EventParticipant.objects.filter(event=event_id, role__in=['organizer', 'committee'])
        if request.user.pk not in team.values_list('participant', flat=True):
            self.serializer_class.Meta.read_only_fields += ['confirmed_organizer']

        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Update an event organization.',
        description='This endpoint updates an event organization. ' +
            'Only the organizer, committee or staff can edit organizations and ' +
            'managers of the organization can confirm the organization.'
    )
    def update(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().update(request, *args, **kwargs)

        instance = self.get_object()
        event = EventOrganizations.objects.get(pk=instance.pk).event
        team = EventParticipant.objects.filter(event=event, role__in=['organizer', 'committee'])
        read_only_fields = ['event', 'organization', 'role']

        if request.user.pk not in instance.organization.managers.values_list('pk', flat=True):
            read_only_fields += ['confirmed_organization']
        if request.user.pk not in team.values_list('participant', flat=True):
            read_only_fields += ['confirmed_organizer']

        for field in read_only_fields:
            if field in request.data:
                field_object = instance._meta.get_field(field)
                instance_value = str(getattr(instance, field_object.attname))
                request_value = request.data[field]

                if instance_value != request_value:
                    return Response(f"You cannot change the '{field}' field", status=status.HTTP_403_FORBIDDEN)

        return super().update(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response("PATCH method is not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    @extend_schema(
        summary='Create an event organization.',
        description='This endpoint creates an event organization. Only Organizer, Commitee or Staff can set a organization as envolved in the event.'
    )
    def create(self, request, *args, **kwargs):
        team = EventParticipant.objects.filter(event=request.data['event'], role__in=['organizer', 'committee'])
        if (
            request.user.pk in team.values_list('participant', flat=True) or 
            request.user.is_staff
        ):
            data = request.data.copy()
            data['confirmed_organizer'] = True
            data['confirmed_organization'] = False
            request._full_data = data
            return super().create(request, *args, **kwargs)
        else:
            return Response("Only the organizer, committee or staff can create a participant", status=status.HTTP_403_FORBIDDEN)

    @extend_schema(
        summary='Delete an event organization.',
        description='This endpoint deletes an event organization. Only Organizer, Commitee, Staff and managers of the organization can delete the organization participation.'
    )
    def destroy(self, request, *args, **kwargs):
        event_id = self.get_object().event.id
        team = EventParticipant.objects.filter(event=event_id, role__in=['organizer', 'committee']).values_list('participant', flat=True)
        managers = self.get_object().organization.managers.values_list('pk', flat=True)
        if (
            request.user.pk in team or
            request.user.is_staff or
            request.user.pk in managers
        ):
            return super().destroy(request, *args, **kwargs)
        else:
            return Response("Only the organizer, committee, staff and managers of the organization can edit this participation", status=status.HTTP_403_FORBIDDEN)