from rest_framework import serializers
from orgs.models import Organization, OrganizationType, TagDiff
from users.models import CustomUser

    
class OrganizationSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['creation_date']

    def get_projects(self, obj):
        from projects.models import ProjectMember
        return ProjectMember.objects.filter(organization=obj, projectmemberacceptance__accepted=True).values_list('project', flat=True)

    def get_events(self, obj):
        from events.models import EventOrganizations
        return EventOrganizations.objects.filter(organization=obj).values_list('event', flat=True)

    

class OrganizationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationType
        fields = '__all__'

class TagDiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagDiff
        fields = ['id', 'tag']