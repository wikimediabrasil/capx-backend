from rest_framework import serializers

from portal.models import (
    PartnerMentorshipAvailability,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMenteeResponse,
)

from drf_spectacular.utils import extend_schema_field, OpenApiTypes

class PartnerMentorshipAvailabilitySerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()

    class Meta:
        model = PartnerMentorshipAvailability
        fields = [
            'id',
            'partner',
            'organization',
            'status',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']

    @extend_schema_field(OpenApiTypes.INT)
    def get_organization(self, obj):
        return obj.partner.organization.id if obj.partner.organization else None

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
