from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from knox.models import AuthToken
from rest_framework import serializers

from campaigns.serializers import CampaignSerializer
from orgs.models import Organization
from users.models import (
    CustomUser,
    Language,
    LanguageProficiency,
    Profile,
    UserBadge,
)


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


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    is_manager = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    language = LanguageProficiencySerializer(source='languageproficiency_set', many=True)
    campaigns = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        read_only_fields = ['is_manager', 'badges']
        fields = "__all__"

    @extend_schema_field({
        'type': 'array',
        'description': 'List of campaigns with full campaign data and role',
        'items': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'metabase_qid': {'type': 'string'},
                'min_start_date': {'type': 'string', 'format': 'date'},
                'max_end_date': {'type': 'string', 'format': 'date'},
                'org_qids': {'type': 'array', 'items': {'type': 'string'}},
                'location_qids': {'type': 'array', 'items': {'type': 'string'}},
                'language_qids': {'type': 'array', 'items': {'type': 'string'}},
                'skill_wikidata_qids': {'type': 'array', 'items': {'type': 'string'}},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'updated_at': {'type': 'string', 'format': 'date-time'},
                'role_wikidata_qid': {'type': 'string'},
            },
        },
    })
    def get_campaigns(self, obj):
        """Return list of campaigns with full campaign data and role."""
        campaigns_data = []
        for pc in obj.profile_campaigns.select_related('campaign').all():
            campaign_data = CampaignSerializer(pc.campaign).data
            campaign_data['role_wikidata_qid'] = pc.role_wikidata_qid
            campaigns_data.append(campaign_data)
        return campaigns_data

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


class UserProfileSerializer(ProfileSerializer):
    """Serializer for user profiles in list/detail views."""
    class Meta(ProfileSerializer.Meta):
        pass
