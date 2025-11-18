from rest_framework import serializers
from users.models import Badge, UserBadge


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = '__all__'


class UserBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBadge
        fields = ['id', 'badge', 'is_displayed', 'progress']
        read_only_fields = ['id', 'badge', 'progress']

    def update(self, instance, validated_data):
        instance.is_displayed = validated_data.get('is_displayed', instance.is_displayed)
        instance.save()
        return instance
