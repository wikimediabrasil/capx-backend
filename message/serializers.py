from rest_framework import serializers
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    message = serializers.CharField(write_only=True, max_length=2000, required=True)
    subject = serializers.CharField(write_only=True, max_length=200, required=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'message',
            'subject',
            'receiver',
            'method',
            'status',
            'error_message',
            'date',
        ]
        read_only_fields = ('status', 'error_message', 'date')