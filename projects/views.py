from .models import Project, ProjectMember, ProjectMemberAcceptance
from rest_framework import serializers, viewsets, status
from .serializers import ProjectSerializer, ProjectMemberSerializer, ProjectMemberAcceptanceSerializer
from orgs.models import Organization
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view


@extend_schema_view(
    list=extend_schema(summary="List projects", description="This endpoint list projects of organizations."),
    retrieve=extend_schema(summary="Retrieve a project", description="This endpoint retrieves a project of an organization."),
)
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    # On creation, set the creator to the current user and create a ProjectMember and ProjectMemberAcceptance object
    def perform_create(self, serializer):
        organization = serializer.validated_data.pop('organization')
        project = serializer.save(creator=self.request.user)
        project_member = ProjectMember.objects.create(project=project, organization=organization)
        ProjectMemberAcceptance.objects.create(project_member=project_member, accepted=True)

    @extend_schema(
        summary="Create a project of an organization",
        description="This endpoint allows managers of organizations and staff to create projects of organizations."
    )
    def create(self, request, *args, **kwargs):
        is_manager = Organization.objects.filter(managers=request.user, pk=request.data['organization']).exists()
        if request.user.is_staff or is_manager:
            return super().create(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    # Only mananger of organizations that are members of the project can update it
    @extend_schema(
        summary="Update a project of an organization",
        description="This endpoint allows managers of organizations that are members of the project and staff to update projects."
    )
    def update(self, request, *args, **kwargs):
        project = self.get_object()
        orgs = project.organizations.values_list('organization', flat=True)
        is_manager = Organization.objects.filter(managers=request.user, pk__in=orgs).exists()
        if request.user.is_staff or is_manager:
            return super().update(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    # Only mananger of organizations that are members of the project can delete it
    @extend_schema(
        summary="Delete a project of an organization",
        description="This endpoint allows managers of organizations that are members of the project and staff to delete projects."
    )
    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        orgs = project.organizations.values_list('organization', flat=True)
        is_manager = Organization.objects.filter(managers=request.user, pk__in=orgs).exists()
        if request.user.is_staff or is_manager:
            return super().destroy(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    @extend_schema(
        exclude=True
    )
    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@extend_schema_view(
    list=extend_schema(summary="List project members", description="This endpoint list project members."),
    retrieve=extend_schema(summary="Retrieve a project member", description="This endpoint retrieves a project member."),
)
class ProjectMemberViewSet(viewsets.ModelViewSet):
    queryset = ProjectMember.objects.all()
    serializer_class = ProjectMemberSerializer

    @extend_schema(
        summary="Create a project member of an organization",
        description="This endpoint allows managers of organizations that are members of the project and staff to add new organization members to the project."
    )
    def create(self, request, *args, **kwargs):
        project = Project.objects.get(pk=request.data['project'])
        orgs = project.organizations.values_list('organization', flat=True)
        is_manager = Organization.objects.filter(managers=request.user, pk__in=orgs).exists()
        if request.user.is_staff or is_manager:
            return super().create(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(
        summary="Delete a project member of an organization",
        description="This endpoint allows managers of organizations that are members of the project to remove themselves from the project, except if they are the only member."
    )
    def destroy(self, request, *args, **kwargs):
        project = Project.objects.get(pk=self.get_object().project.id)
        orgs = project.organizations.values_list('organization', flat=True)
        is_manager = Organization.objects.filter(managers=request.user, pk__in=orgs).exists()
        if is_manager and project.organizations.count() > 1:
            return super().destroy(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)


@extend_schema_view(
    list=extend_schema(summary="List project member acceptances", description="This endpoint list project member acceptances."),
    retrieve=extend_schema(summary="Retrieve a project member acceptance", description="This endpoint retrieves a project member acceptance."),
)
class ProjectMemberAcceptanceViewSet(viewsets.ModelViewSet):
    queryset = ProjectMemberAcceptance.objects.all()
    serializer_class = ProjectMemberAcceptanceSerializer

    @extend_schema(
        summary="Accept a project member",
        description="This endpoint allows managers of the invited organization to accept project members."
    )
    def create(self, request, *args, **kwargs):
        # Check if there is already a ProjectMemberAcceptance object for the project member
        project_member = ProjectMember.objects.get(pk=request.data['project_member'])
        if ProjectMemberAcceptance.objects.filter(project_member=project_member).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Only mananger of invited organization can accept project members
        if Organization.objects.filter(managers=request.user, pk=project_member.organization.id).exists():
            return super().create(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
    
    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)