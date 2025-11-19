from rest_framework import serializers

from users.models import Profile
from .account_serializers import UserSerializer


class UsersBySkillSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Profile
        fields = [
            'user', 'skills_known', 'skills_available', 'skills_wanted',
        ]
        read_only_fields = ['skills_known', 'skills_available', 'skills_wanted']


class UsersByTagSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')

    class Meta:
        model = Profile
        fields = ['id', 'display_name', 'username', 'profile_image']

