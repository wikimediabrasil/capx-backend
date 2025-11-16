from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema
from users.models import Badge, UserBadge
from users.serializers import BadgeSerializer, UserBadgeSerializer


@extend_schema_view(
    list=extend_schema(
        summary='List all badges.',
        description='This endpoint lists all badges.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a badge by ID.',
        description='This endpoint retrieves a badge by its ID.',
    ),
)
class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer


@extend_schema_view(
    list=extend_schema(
        summary='List all user badges.',
        description='This endpoint lists all user badges.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a user badge by ID.',
        description='This endpoint retrieves a user badge by its ID.',
    ),
    update=extend_schema(
        summary='Update a user badge.',
        description='This endpoint updates a user badge.',
    ),
)
class UserBadgeViewSet(viewsets.ModelViewSet):
    queryset = UserBadge.objects.all()
    serializer_class = UserBadgeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user == request.user:
            return super().update(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def create(self, request, *args, **kwargs):
        return Response({'message': 'Creating user badges is not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Deleting user badges is not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Partial updates are not allowed for user badges.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)