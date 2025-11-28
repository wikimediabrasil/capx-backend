from rest_framework import serializers
from users.models import Profile
from orgs.models import Organization


class RecommendationUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    matches = serializers.IntegerField(source='match_count')

    class Meta:
        model = Profile
        fields = ['id', 'display_name', 'username', 'avatar', 'matches']


class RecommendationOrganizationSerializer(serializers.ModelSerializer):
    matches = serializers.IntegerField(source='match_count')
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'display_name', 'profile_image', 'acronym', 'matches']

    def get_display_name(self, obj):
        en = obj.i18n_names.filter(language_code='en').first()
        return en.name if en else ''
