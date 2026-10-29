from django.core.validators import RegexValidator
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from campaigns.models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    org_qids = serializers.SerializerMethodField()
    location_qids = serializers.SerializerMethodField()
    language_qids = serializers.SerializerMethodField()
    skill_capx_ids = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            "id",
            "metabase_qid",
            "min_start_date",
            "max_end_date",
            "org_qids",
            "location_qids",
            "language_qids",
            "skill_capx_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_org_qids(self, obj) -> list[str]:
        return obj.get_pipe_separated_as_array("org_qids")

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_location_qids(self, obj) -> list[str]:
        return obj.get_pipe_separated_as_array("location_qids")

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_language_qids(self, obj) -> list[str]:
        return obj.get_pipe_separated_as_array("language_qids")

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_skill_capx_ids(self, obj) -> list[str]:
        return obj.get_pipe_separated_as_array("skill_capx_ids")


class CampaignProfileSerializer(serializers.ModelSerializer):
    """Serializer for linking a profile to a campaign with role."""

    role_wikidata_qid = serializers.CharField(
        default="Q56512863",
        help_text="Wikidata Qid of the role (default: Q56512863 - participant).",
    )

    class Meta:
        model = Campaign
        fields = ("id", "metabase_qid", "role_wikidata_qid")

    def validate_role_wikidata_qid(self, value):
        """Validate Wikidata Qid format."""
        validator = RegexValidator(
            regex=r"^Q[1-9]\d*$",
            message="Invalid Wikidata Qid format. The format should be Q12345",
        )
        validator(value)
        return value
