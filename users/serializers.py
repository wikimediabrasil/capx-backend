from rest_framework import serializers
from .models import Profile, CustomUser
from .submodels import Territory, Language, WikimediaProject
from orgs.models import Organization
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

   
class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
        ]
        read_only_fields = [
            'username',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
        ]

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
        fields = ['id', 'wikimedia_project_name', 'wikimedia_project_code']

class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ['id', 'display_name']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    is_manager = serializers.SerializerMethodField()
    
    class Meta:
        model = Profile
        fields = [
            'user',
            'profile_image',
            'display_name',
            'pronoun',
            'about',
            'wikidata_qid',
            'wiki_alt',
            'territory',
            'language',
            'affiliation',
            'wikimedia_project',
            'team',
            'skills_known',
            'skills_available',
            'skills_wanted',
            'contact',
            'social',
            'is_manager',
        ]
        read_only_fields = [
            'is_manager',
        ]

    @extend_schema_field({
        'type': 'array',
        'description': 'List of organization IDs where the user is a manager',
        'items': {'type': 'integer'}
    })
    def get_is_manager(self, obj):
        return list(Organization.objects.filter(managers=obj.user).values_list('id', flat=True))

    # Override the update method to allow write access to the nested user object
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data is not None:
            user = instance.user
            user.email = user_data.get('email', user.email)
            user.save()
        return super().update(instance, validated_data)

class UsersBySkillSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Profile
        fields = [
            'user',
            'skills_known',
            'skills_available',
            'skills_wanted',
        ]
        read_only_fields = [
            'skills_known',
            'skills_available',
            'skills_wanted',
        ]
   

class UsersByTagSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')

    class Meta:
        model = Profile
        fields = [
            'id', 
            'display_name', 
            'username', 
            'profile_image'
        ]
