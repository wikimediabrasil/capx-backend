from rest_framework import serializers
from orgs.models import Organization, OrganizationType, TagDiff, Document
from orgs.models import OrganizationName
from users.models import CustomUser
from drf_spectacular.utils import extend_schema_field, OpenApiTypes, extend_schema_serializer

@extend_schema_field(OpenApiTypes.STR)
class LegacyDisplayNameField(serializers.Field):
    """Virtual, deprecated field that maps to the English translation only.

    - Read: returns English (en) display name or empty string.
    - Write: accepts a non-empty string and will upsert the English translation.
    """

    def to_representation(self, value: Organization) -> str:
        en = getattr(value, 'i18n_names', None)
        if en is not None:
            row = en.filter(language_code='en').only('name').first()
            return row.name if row else ""
        return ""

    def to_internal_value(self, data):
        if data is None:
            return {}
        if not isinstance(data, str):
            raise serializers.ValidationError("display_name must be a string")
        cleaned = data.strip()
        if cleaned == "":
            # Allow blank only to mean "no change" on update; validation will enforce required on create
            return {}
        return { 'display_name': cleaned }


class OrganizationSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()
    # Deprecated virtual field: reads/writes English translation only
    display_name = LegacyDisplayNameField(source='*', required=False, help_text='Deprecated: use i18n translations. Writing here updates only the English (en) variant.')
    names = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['creation_date']

    @extend_schema_field({
        'type': 'array',
        'description': 'List of localized names for the organization',
        'items': {'type': 'object',
                  'properties': {
                      'language_code': {'type': 'string'},
                      'name': {'type': 'string'},
                  }}
    })
    def get_names(self, obj):
        # Return only language_code and name, omit id and organization
        return list(obj.i18n_names.all().values('language_code', 'name'))

    @extend_schema_field({
        'type': 'array',
        'description': 'List of project\' IDs that are associated with the organization',
        'items': {'type': 'integer'}
    })
    def get_projects(self, obj):
        from projects.models import ProjectMember
        return ProjectMember.objects.filter(organization=obj, projectmemberacceptance__accepted=True).values_list('project', flat=True)

    @extend_schema_field({
        'type': 'array',
        'description': 'List of event\' IDs that are associated with the organization',
        'items': {'type': 'integer'}
    })
    def get_events(self, obj):
        from events.models import Events
        return Events.objects.filter(organization=obj).values_list('id', flat=True)

    def _upsert_en_translation(self, org: Organization, value: str | None):
        if value is None:
            return
        value = value.strip()
        if value == "":
            return
        # Update or create the English translation row
        # Using related manager to avoid extra imports
        en = org.i18n_names.filter(language_code='en').first()
        if en:
            if en.name != value:
                en.name = value
                en.save(update_fields=['name'])
        else:
            org.i18n_names.create(language_code='en', name=value)

    def create(self, validated_data):
        # Extract deprecated display_name for English translation. Mandatory on create.
        display_name = validated_data.pop('display_name', None)
        if not display_name or display_name.strip() == "":
            raise serializers.ValidationError({
                'display_name': 'This field is required and must provide the English (en) name.'
            })
        org = super().create(validated_data)
        self._upsert_en_translation(org, display_name)
        return org

    def update(self, instance, validated_data):
        display_name = validated_data.pop('display_name', None)
        org = super().update(instance, validated_data)
        self._upsert_en_translation(org, display_name)
        return org

    
class OrganizationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationType
        fields = '__all__'


class TagDiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagDiff
        fields = ['id', 'tag']

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'url']


class OrganizationNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationName
        fields = ['id', 'organization', 'language_code', 'name']