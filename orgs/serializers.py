from rest_framework import serializers
from orgs.models import Organization, OrganizationType, TagDiff, Document
from users.models import CustomUser
from drf_spectacular.utils import extend_schema_field, OpenApiTypes

    
class OrganizationSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['creation_date']

    @extend_schema_field({
        'type': 'array',
        'description': 'List of project\' IDs that are associated with the organization',
        'items': {'type': 'integer'}
    })
    def get_projects(self, obj):
        from projects.models import ProjectMember
        return ProjectMember.objects.filter(organization=obj, projectmemberacceptance__accepted=True).values_list('project', flat=True)

    @extend_schema_field({
        'type': 'array',
        'description': 'List of event\' IDs that are associated with the organization',
        'items': {'type': 'integer'}
    })
    def get_events(self, obj):
        from events.models import EventOrganizations
        return EventOrganizations.objects.filter(organization=obj).values_list('event', flat=True)
    
    def validate_choose_events(self, choose_events):
        from events.models import EventOrganizations
        
        # Get organization ID from context if it's an update operation
        org_id = None
        if self.instance:
            org_id = self.instance.id
        
        # If it's a create operation, we can't validate yet as the organization doesn't exist
        if not org_id:
            return choose_events
            
        # Get all event IDs associated with this organization
        valid_events = EventOrganizations.objects.filter(organization_id=org_id).values_list('event', flat=True)
        valid_events_set = set(valid_events)
        
        # Check if all chosen events are in the list of valid events
        for event in choose_events:
            if event.id not in valid_events_set:
                raise serializers.ValidationError(
                    f"Event with ID {event.id} is not associated with this organization. "
                    f"It must be in the organization's 'events' field."
                )
                
        return choose_events

    
class OrganizationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationType
        fields = '__all__'


class TagDiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagDiff
        fields = ['id', 'tag']

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'url']