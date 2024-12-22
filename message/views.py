from .models import Message
from .serializers import MessageSerializer
from rest_framework import status, viewsets, filters


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    queryset = Message.objects.all()

    # Always set field "sender" as the current user
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        serializer_class.Meta.read_only_fields = ('sender',)
        return serializer_class

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
