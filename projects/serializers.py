from rest_framework import serializers
from projects.models import Project, ProjectMember, ProjectMemberAcceptance
from orgs.models import Organization

class ProjectSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), write_only=True)

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['creation_date', 'organization']

class ProjectMemberSerializer(serializers.ModelSerializer):
    accepted = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = '__all__'

    def get_accepted(self, obj):
        accepted = ProjectMemberAcceptance.objects.filter(project_member=obj).first()
        return accepted.accepted if accepted else False

class ProjectMemberAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMemberAcceptance
        fields = '__all__'