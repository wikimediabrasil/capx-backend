from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes
from users.models import SavedItem
from users.serializers import SavedItemSerializer


@extend_schema_view(
    list=extend_schema(
        summary='List all items saved by the logged-in user.',
        description='This endpoint lists all items saved by the logged-in user.',
    ),
    create=extend_schema(
        summary='Create a new saved item.',
        description='This endpoint creates a new saved item.',
    ),
    retrieve=extend_schema(
        summary='Retrieve a saved item by ID.',
        description='This endpoint retrieves a saved item by its ID.',
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
                required=True,
                description='The ID of the saved item to retrieve.',
            ),
        ],
    ),
    destroy=extend_schema(
        summary='Delete a saved item by ID.',
        description='This endpoint deletes a saved item by its ID.',
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
                required=True,
                description='The ID of the saved item to retrieve.',
            ),
        ],
    ),
)
class SavedItemViewSet(viewsets.ModelViewSet):
    serializer_class = SavedItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedItem.objects.filter(user=self.request.user).exclude(related_user__is_active=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        relation = request.data.get('relation')
        entity = request.data.get('entity')
        entity_id = request.data.get('entity_id')

        if entity == 'org':
            existing_item = SavedItem.objects.filter(
                user=user, relation=relation, entity='org', related_org_id=entity_id
            ).first()
        elif entity == 'user':
            existing_item = SavedItem.objects.filter(
                user=user, relation=relation, entity='user', related_user_id=entity_id
            ).first()
        else:
            return Response({'message': 'Invalid entity type.'}, status=status.HTTP_400_BAD_REQUEST)

        if existing_item:
            serializer = self.get_serializer(existing_item)
            return Response(serializer.data, status=status.HTTP_208_ALREADY_REPORTED)

        return super().create(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        response = {'message': 'Partial updates are not allowed for saved items.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        response = {'message': 'Updates are not allowed for saved items.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

