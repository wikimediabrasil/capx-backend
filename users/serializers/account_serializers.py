from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from drf_spectacular.types import OpenApiTypes
from django.shortcuts import get_object_or_404

from users.models import Profile, CustomUser, LanguageProficiency, UserBadge
from users.models import Language
from orgs.models import Organization
from knox.models import AuthToken


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'is_staff', 'is_active', 'date_joined',
        ]
        read_only_fields = ['username', 'is_staff', 'is_active', 'date_joined']


class LanguageProficiencySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='language.id')

    class Meta:
        model = LanguageProficiency
        fields = ['id', 'proficiency']


@extend_schema_serializer(deprecate_fields=['profile_image'])
class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    is_manager = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    language = LanguageProficiencySerializer(source='languageproficiency_set', many=True)

    class Meta:
        model = Profile
        fields = [
            'user', 'last_update', 'last_login', 'profile_image', 'avatar', 'display_name', 'pronoun', 'about',
            'wikidata_qid', 'wiki_alt', 'territory', 'language', 'affiliation', 'wikimedia_project', 'team',
            'skills_known', 'skills_available', 'skills_wanted', 'contact', 'social', 'is_manager', 'badges',
            'automated_lets_connect',
        ]
        read_only_fields = ['is_manager', 'badges']

    @extend_schema_field({
        'type': 'array', 'description': 'List of organization IDs where the user is a manager', 'items': {'type': 'integer'}
    })
    def get_is_manager(self, obj):
        return list(Organization.objects.filter(managers=obj.user).values_list('id', flat=True))

    @extend_schema_field({
        'type': 'array', 'description': 'List of badge IDs associated with the user', 'items': {'type': 'integer'}
    })
    def get_badges(self, obj):
        return list(UserBadge.objects.filter(user=obj.user, is_displayed=True, progress=100).values_list('badge__id', flat=True))

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_last_login(self, obj):
        token = AuthToken.objects.filter(user=obj.user).order_by('-created').first()
        return token.created if token else None

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
