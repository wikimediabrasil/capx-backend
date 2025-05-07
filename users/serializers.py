from rest_framework import serializers
from .models import Profile, CustomUser, LanguageProficiency, SavedItem, LetsConnectLog
from .submodels import Territory, Language, WikimediaProject, Avatar
from orgs.models import Organization
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from drf_spectacular.types import OpenApiTypes
from django.shortcuts import get_object_or_404

   
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
        fields = ['id', 'wikimedia_project_name', 'wikimedia_project_code', 'wikimedia_project_picture']

class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ['id', 'display_name']

class LanguageProficiencySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='language.id')

    class Meta:
        model = LanguageProficiency
        fields = ['id', 'proficiency']

class AvatarSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Avatar
        fields = ['id', 'avatar_url']

@extend_schema_serializer(deprecate_fields = ['profile_image'])
class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    is_manager = serializers.SerializerMethodField()
    language = LanguageProficiencySerializer(source='languageproficiency_set', many=True)
    
    class Meta:
        model = Profile
        fields = [
            'user',
            'profile_image',
            'avatar',
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

        language_proficiency_data = validated_data.pop('languageproficiency_set', None)
        if language_proficiency_data is not None:
            for lang_prof in language_proficiency_data:
                language = get_object_or_404(Language, id=lang_prof['language']['id'])
                proficiency = lang_prof['proficiency']
                lang_prof_instance, _ = LanguageProficiency.objects.get_or_create(profile=instance, language=language)
                lang_prof_instance.proficiency = proficiency
                lang_prof_instance.save()

            # Delete any language proficiencies that were not included in the request
            instance.languageproficiency_set.exclude(
                language__in=[lang_prof['language']['id'] for lang_prof in language_proficiency_data]
                ).delete()

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

@extend_schema_field({
    'type': 'integer',
    'description': 'ID of the organization or user',
})
class EntityIdField(serializers.Field):
    def get_attribute(self, instance):
        """
        Dynamically retrieve the entity_id based on the entity type.
        """
        if instance.entity == 'org':
            return instance.related_org.id if instance.related_org else None
        elif instance.entity == 'user':
            return instance.related_user.id if instance.related_user else None

    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        return data


class SavedItemSerializer(serializers.ModelSerializer):
    entity_id = EntityIdField()

    class Meta:
        model = SavedItem
        fields = ['id', 'relation', 'entity', 'entity_id', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, data):
        entity = data.get('entity')
        entity_id = data.get('entity_id')

        if entity == 'org':
            if not Organization.objects.filter(id=entity_id).exists():
                raise serializers.ValidationError("Invalid organization ID.")
        elif entity == 'user':
            if not CustomUser.objects.filter(id=entity_id).exists():
                raise serializers.ValidationError("Invalid user ID.")
                
        return data

    def create(self, validated_data):
        entity = validated_data['entity']
        entity_id = validated_data.pop('entity_id')

        if entity == 'org':
            validated_data['related_org'] = Organization.objects.get(id=entity_id)
        elif entity == 'user':
            validated_data['related_user'] = CustomUser.objects.get(id=entity_id)

        return super().create(validated_data)


class LetsConnectLogSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True)
    email = serializers.CharField(write_only=True)
    role = serializers.CharField(write_only=True)
    area = serializers.CharField(write_only=True)
    gender = serializers.CharField(write_only=True)
    age = serializers.CharField(write_only=True)

    class Meta:
        model = LetsConnectLog
        fields = [
            'full_name',
            'email',
            'role',
            'area',
            'gender',
            'age',
            'user',
            'confirmation',
        ]
        extra_kwargs = {
            'user': {'read_only': True},
            'confirmation': {'read_only': True},
        }
