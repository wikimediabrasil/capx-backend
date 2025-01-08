from .models import Project, ProjectMember, ProjectMemberAcceptance
from rest_framework import serializers
from .serializers import ProjectSerializer, ProjectMemberSerializer, ProjectMemberAcceptanceSerializer
from orgs.models import Organization
from rest_framework import viewsets

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    # On creation, set the creator to the current user
    def perform_create(self, serializer):
        organization = serializer.validated_data.pop('organization')
        project = serializer.save(creator=self.request.user)
        ProjectMember.objects.create(project=project, organization=organization)

    # Only mananger of organizations and staff can create projects
    def create(self, request, *args, **kwargs):
        if request.user.is_staff or request.user.is_manager:
            return super().create(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    # Only mananger of organizations that are members of the project can update it
    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if request.user.is_staff or request.user.is_manager and project.projectmember_set.filter(organization__manager=request.user).exists():
            return super().update(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    # Only mananger of organizations that are members of the project can delete it
    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if request.user.is_staff or request.user.is_manager and project.projectmember_set.filter(organization__manager=request.user).exists():
            return super().destroy(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)


class ProjectMemberViewSet(viewsets.ModelViewSet):
    queryset = ProjectMember.objects.all()
    serializer_class = ProjectMemberSerializer

    # Only mananger of organizations that are members of the project can create project members
    def create(self, request, *args, **kwargs):
        project = Project.objects.get(pk=request.data['project'])
        if request.user.is_staff or request.user.is_manager and project.projectmember_set.filter(organization__manager=request.user).exists():
            return super().create(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    # Only mananger of organizations that are members of the project can update project members
    def update(self, request, *args, **kwargs):
        project = Project.objects.get(pk=request.data['project'])
        if request.user.is_staff or request.user.is_manager and project.projectmember_set.filter(organization__manager=request.user).exists():
            return super().update(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    # Only mananger of organizations that are members of the project can delete project members
    def destroy(self, request, *args, **kwargs):
        project = Project.objects.get(pk=request.data['project'])
        if request.user.is_staff or request.user.is_manager and project.projectmember_set.filter(organization__manager=request.user).exists():
            return super().destroy(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)


class ProjectMemberAcceptanceViewSet(viewsets.ModelViewSet):
    queryset = ProjectMemberAcceptance.objects.all()
    serializer_class = ProjectMemberAcceptanceSerializer

    def create(self, request, *args, **kwargs):
        # Check if there is already a ProjectMemberAcceptance object for the project member
        project_member = ProjectMember.objects.get(pk=request.data['project_member'])
        if ProjectMemberAcceptance.objects.filter(project_member=project_member).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Only mananger of invited organization can accept project members
        if Organization.objects.filter(managers=request.user, pk=request.data['organization']).exists():
            return super().create(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)