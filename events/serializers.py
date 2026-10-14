from rest_framework import serializers
from .models import Events, Participation

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Events
        fields = '__all__'
        read_only_fields = ['creator', 'created_at', 'updated_at']

class ParticipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
