from rest_framework import serializers

from portal.models import (
    Partner,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMenteeResponse,
)

from drf_spectacular.utils import extend_schema_field, OpenApiTypes

class PartnerSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            'id',
            'name',
            'mentorship',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.INT)
    def get_id(self, obj):
        return str(obj.organization_id)

    @extend_schema_field(OpenApiTypes.STR)
    def get_name(self, obj):
        return str(obj.organization.i18n_names.filter(language_code='en').first().name)

class PartnerMentorshipFormMentorSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerMentorshipFormMentor
        fields = [
            'id',
            'partner',
            'json',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

class PartnerMentorshipFormMenteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerMentorshipFormMentee
        fields = [
            'id',
            'partner',
            'json',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PartnerMentorshipFormMentorResponseSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = PartnerMentorshipFormMentorResponse
        fields = [
            'form',
            'data',
            'user',
        ]


class PartnerMentorshipFormMenteeResponseSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = PartnerMentorshipFormMenteeResponse
        fields = [
            'form',
            'data',
            'user',
        ]
