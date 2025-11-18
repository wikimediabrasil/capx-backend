from rest_framework import viewsets
from drf_spectacular.utils import extend_schema_view, extend_schema
from users.models import WikimediaProject, Territory, Avatar
from users.serializers import WikimediaProjectSerializer, TerritorySerializer, AvatarSerializer


@extend_schema_view(
    list=extend_schema(
        summary='List all Wikimedia projects.',
        description='This endpoint lists all Wikimedia projects.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a Wikimedia project by ID.',
        description='This endpoint retrieves a Wikimedia project by its ID.',
    ),
)
class WikimediaProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WikimediaProject.objects.all()
    serializer_class = WikimediaProjectSerializer

@extend_schema_view(
    list=extend_schema(
        summary='List all territories.',
        description='This endpoint lists all territories.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a territory by ID.',
        description='This endpoint retrieves a territory by its ID.',
    ),
)
class TerritoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Territory.objects.all()
    serializer_class = TerritorySerializer

@extend_schema_view(
    list=extend_schema(
        summary='List all avatars.',
        description='This endpoint lists all avatars.',
    ),
    retrieve=extend_schema(
        summary='Retrieve an avatar by ID.',
        description='This endpoint retrieves an avatar by its ID.',
    ),
)
class AvatarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Avatar.objects.all()
    serializer_class = AvatarSerializer