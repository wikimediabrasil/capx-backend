from .models import Message
from .serializers import MessageSerializer
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

@extend_schema_view(
    list=extend_schema(
        summary="List all messages.",
        description="This endpoint lists all messages sent by the user. If the user is a staff member, all messages are listed."
    ),
    create=extend_schema(
        summary="Create a new message.",
        description="This endpoint creates a new message."
    ),
    retrieve=extend_schema(
        summary="Retrieve a message.",
        description="This endpoint retrieves a message by its ID.",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)]
    )
)
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Message.objects.all()
        else:
            return Message.objects.filter(sender=user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        serializer_class.Meta.read_only_fields = ('sender',)
        return serializer_class

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)