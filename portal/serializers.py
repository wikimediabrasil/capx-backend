from rest_framework import serializers

from portal.models import (
    Partner,
    PartnerMentorshipSettings,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMenteeResponse,
)

from drf_spectacular.utils import extend_schema_field, OpenApiTypes

class PartnerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='organization.id', read_only=True)
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

    @extend_schema_field(OpenApiTypes.STR)
    def get_name(self, obj):
        return str(obj.organization.i18n_names.filter(language_code='en').first().name)


class PartnerSettingsSerializer(serializers.ModelSerializer):
    organization = serializers.IntegerField(source='partner.organization.id', read_only=True)
    territory = serializers.IntegerField(source='territory.id', read_only=True, allow_null=True)
    territory_name = serializers.SerializerMethodField()

    class Meta:
        model = PartnerMentorshipSettings
        fields = [
            'id',
            'organization',
            'description',
            'registration_open_date',
            'registration_close_date',
            'territory',
            'territory_name',
            'skills',
            'languages',
            'mentor_form',
            'mentee_form',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.STR)
    def get_territory_name(self, obj):
        return obj.territory.territory_name if obj.territory_id else None


class PartnerMentorshipFormMentorSerializer(serializers.ModelSerializer):
    organization = serializers.IntegerField(source='partner.organization.id', read_only=True)
    counter = serializers.SerializerMethodField()
    public_key_id = serializers.IntegerField(source='public_key.id', read_only=True, allow_null=True)
    public_key_fingerprint = serializers.CharField(source='public_key.fingerprint', read_only=True, allow_blank=True, allow_null=True)
    public_key_created_at = serializers.DateTimeField(source='public_key.created_at', read_only=True, allow_null=True)

    class Meta:
        model = PartnerMentorshipFormMentor
        fields = [
            'id',
            'organization',
            'counter',
            'public_key_id',
            'public_key_fingerprint',
            'public_key_created_at',
            'json',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(OpenApiTypes.INT)
    def get_counter(self, obj):
        return PartnerMentorshipFormMentorResponse.objects.filter(form=obj).count()

class PartnerMentorshipFormMenteeSerializer(serializers.ModelSerializer):
    organization = serializers.IntegerField(source='partner.organization.id', read_only=True)
    counter = serializers.SerializerMethodField()
    public_key_id = serializers.IntegerField(source='public_key.id', read_only=True, allow_null=True)
    public_key_fingerprint = serializers.CharField(source='public_key.fingerprint', read_only=True, allow_blank=True, allow_null=True)
    public_key_created_at = serializers.DateTimeField(source='public_key.created_at', read_only=True, allow_null=True)

    class Meta:
        model = PartnerMentorshipFormMentee
        fields = [
            'id',
            'organization',
            'counter',
            'public_key_id',
            'public_key_fingerprint',
            'public_key_created_at',
            'json',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(OpenApiTypes.INT)
    def get_counter(self, obj):
        return PartnerMentorshipFormMenteeResponse.objects.filter(form=obj).count()


class PartnerMentorshipFormMentorResponseSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    public_key_id = serializers.IntegerField(source='form.public_key_id', read_only=True, allow_null=True)
    public_key_fingerprint = serializers.CharField(source='form.public_key.fingerprint', read_only=True, allow_blank=True, allow_null=True)
    public_key_created_at = serializers.DateTimeField(source='form.public_key.created_at', read_only=True, allow_null=True)
    encrypted_with_public_key_id = serializers.IntegerField(source='encrypted_with_public_key_id_snapshot', read_only=True, allow_null=True)
    encrypted_with_public_key_fingerprint = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)

    class Meta:
        model = PartnerMentorshipFormMentorResponse
        fields = [
            'form',
            'data',
            'user',
            'public_key_id',
            'public_key_fingerprint',
            'public_key_created_at',
            'encrypted_with_public_key_id',
            'encrypted_with_public_key_fingerprint',
        ]


class PartnerMentorshipFormMenteeResponseSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    public_key_id = serializers.IntegerField(source='form.public_key_id', read_only=True, allow_null=True)
    public_key_fingerprint = serializers.CharField(source='form.public_key.fingerprint', read_only=True, allow_blank=True, allow_null=True)
    public_key_created_at = serializers.DateTimeField(source='form.public_key.created_at', read_only=True, allow_null=True)
    encrypted_with_public_key_id = serializers.IntegerField(source='encrypted_with_public_key_id_snapshot', read_only=True, allow_null=True)
    encrypted_with_public_key_fingerprint = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)

    class Meta:
        model = PartnerMentorshipFormMenteeResponse
        fields = [
            'form',
            'data',
            'user',
            'public_key_id',
            'public_key_fingerprint',
            'public_key_created_at',
            'encrypted_with_public_key_id',
            'encrypted_with_public_key_fingerprint',
        ]
