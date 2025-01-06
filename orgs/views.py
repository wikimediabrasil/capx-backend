from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from .models import Organization, OrganizationType
from .serializers import OrganizationSerializer, OrganizationTypeSerializer
from users.models import CustomUser as User, Territory
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework.decorators import action

@extend_schema_view(
    list=extend_schema(
        summary='List all organizations.',
        description='This endpoint lists all organizations that has been activated (i.e. has at least one manager). If the user is a staff member, all organizations are listed.',
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

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Organization.objects.all()
        else:
            return Organization.objects.filter(managers__isnull=False)
    
    @extend_schema(
        summary='Retrieve an organization by ID.',
        description='This endpoint retrieves an organization by its ID.',
    )  
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        data['territory'] = [Territory.objects.get(id=id).territory_name for id in data['territory']]
        data['managers'] = [User.objects.get(id=id).username for id in data['managers']]
        return Response(data)

    @extend_schema(
        summary='Create a new organization.',
        description='This endpoint creates a new organization. Only staff members can create organizations.',
    )
    def create(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().create(request, *args, **kwargs)
        return Response("You do not have permission to create an organization.", status=status.HTTP_403_FORBIDDEN)

    @extend_schema(
        summary='Updates a organization.',
        description='This endpoint updates an organization by its ID. Only staff members and managers of the organization can update it.',
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
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

    @extend_schema(
        summary='Check if user is manager.',
        description='Debug endpoint to check if current user is manager of any organization.',
    )
    @action(detail=False, methods=['get'])
    def check_manager(self, request):
        user_orgs = Organization.objects.filter(managers=request.user)
        return Response({
            "is_manager": user_orgs.exists(),
            "organizations": [
                {"id": org.id, "name": org.display_name}
                for org in user_orgs
            ]
        })


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