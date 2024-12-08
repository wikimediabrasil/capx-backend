from .models import Message
from .serializers import MessageSerializer
from rest_framework import status, viewsets, filters


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    queryset = Message.objects.all()