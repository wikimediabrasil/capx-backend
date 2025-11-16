from rest_framework import serializers

from users.submodels import Territory, Language, WikimediaProject, Avatar
from orgs.models import Organization


class TerritorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Territory
        fields = ['id', 'territory_name', 'parent_territory']


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'language_name', 'language_autonym', 'language_code']


class WikimediaProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = WikimediaProject
        fields = ['id', 'wikimedia_project_name', 'wikimedia_project_code', 'wikimedia_project_picture']


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'display_name']


class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avatar
        fields = ['id', 'avatar_url']
