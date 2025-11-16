from rest_framework import serializers
from users.models import LetsConnectLog


class LetsConnectLogSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.CharField(write_only=True, required=True)
    area = serializers.CharField(write_only=True, required=False, allow_blank=True)
    gender = serializers.CharField(write_only=True, required=False, allow_blank=True)
    age = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = LetsConnectLog
        fields = [
            'full_name', 'email', 'role', 'area', 'gender', 'age', 'user', 'confirmation', 'timestamp',
        ]
        extra_kwargs = {
            'user': {'read_only': True},
            'confirmation': {'read_only': True},
            'timestamp': {'read_only': True},
        }
