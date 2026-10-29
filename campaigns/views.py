from django_filters import rest_framework as django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from campaigns.models import Campaign
from campaigns.serializers import CampaignProfileSerializer, CampaignSerializer
from skills.models import Skill
from users.models import ProfileCampaign


class CampaignFilter(django_filters.FilterSet):
    """Filter set for Campaign model."""

    skills = django_filters.ModelMultipleChoiceFilter(
        queryset=Skill.objects.all(),
        field_name="skills",
        conjoined=False,
        label="Filter by skill IDs (comma-separated)",
    )

    class Meta:
        model = Campaign
        fields = {  # noqa: RUF012
            "metabase_qid": ["exact"],
            "min_start_date": ["exact", "gte", "lte"],
            "max_end_date": ["exact", "gte", "lte"],
        }


@extend_schema_view(
    list=extend_schema(
        summary="List all campaigns.",
        description="This endpoint lists all campaigns with filtering and ordering options.",
        parameters=[
            OpenApiParameter(
                name="metabase_qid",
                description="Filter by Metabase QID (exact match).",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="min_start_date",
                description="Filter by minimum start date (format: YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="max_end_date",
                description="Filter by maximum end date (format: YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="skills",
                description="Filter by skill IDs (comma-separated).",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="ordering",
                description='Sort campaigns by field. Prefix with "-" for descending order. Options: metabase_qid, min_start_date, max_end_date, created_at, updated_at.',
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a campaign by ID.",
        description="This endpoint retrieves a campaign by its ID.",
    ),
)
class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CampaignSerializer
    queryset = Campaign.objects.all()
    filter_backends = (
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    )
    filterset_class = CampaignFilter
    ordering_fields = (
        "metabase_qid",
        "min_start_date",
        "max_end_date",
        "created_at",
        "updated_at",
    )
    search_fields = ("metabase_qid",)


@extend_schema_view(
    list=extend_schema(
        summary="List campaigns for the authenticated user.",
        description="This endpoint lists campaigns associated with the authenticated user's profile.",
        parameters=[
            OpenApiParameter(
                name="role_wikidata_qid",
                description="Filter by role Wikidata QID.",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a specific campaign for the authenticated user.",
        description="This endpoint retrieves a specific campaign for the authenticated user.",
    ),
    create=extend_schema(
        summary="Add a campaign to the authenticated user's profile.",
        description=(
            "This endpoint adds a campaign to the authenticated user's profile "
            "with a role (default: Q56512863 - participant).\n\n"
            "Request body:\n"
            "- **campaign** (integer, required): ID of the campaign to add\n"
            "- **role_wikidata_qid** (string, optional): Wikidata QID of the role "
            "(default: Q56512863)"
        ),
        request=CampaignProfileSerializer,
        responses={201: CampaignSerializer},
    ),
    destroy=extend_schema(
        summary="Remove a campaign from the authenticated user's profile.",
        description="This endpoint removes a campaign from the authenticated user's profile.",
        parameters=[
            OpenApiParameter(
                name="id",
                description="ID of the campaign to remove from profile.",
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
            ),
        ],
    ),
)
class UserCampaignViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user's campaigns through their profile."""

    serializer_class = CampaignSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Campaign.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "id"
    http_method_names = ("get", "post", "delete", "head", "options")

    def get_serializer_class(self):
        if self.action == "create":
            return CampaignProfileSerializer
        return CampaignSerializer

    def get_queryset(self):
        return Campaign.objects.filter(profiles__user=self.request.user).distinct()

    def create(self, request, *args, **kwargs):
        """Add a campaign to the user's profile."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        campaign_id = serializer.validated_data["campaign"]
        role_wikidata_qid = serializer.validated_data.get("role_wikidata_qid", "Q56512863")

        campaign = Campaign.objects.get(pk=campaign_id)

        profile = request.user.profile
        if ProfileCampaign.objects.filter(profile=profile, campaign=campaign).exists():
            return Response(
                {"detail": "Campaign already linked to your profile."},
                status=status.HTTP_409_CONFLICT,
            )

        ProfileCampaign.objects.create(
            profile=profile, campaign=campaign, role_wikidata_qid=role_wikidata_qid
        )

        serializer = CampaignSerializer(campaign)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Remove a campaign from the user's profile."""
        campaign_id = kwargs.get("id")
        if not str(campaign_id).isdigit():
            return Response(
                {"detail": "Campaign ID must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            campaign = Campaign.objects.get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
            )

        profile = request.user.profile
        profile_campaign = ProfileCampaign.objects.filter(
            profile=profile, campaign=campaign
        ).first()

        if not profile_campaign:
            return Response(
                {"detail": "Campaign not linked to your profile."},
                status=status.HTTP_404_NOT_FOUND,
            )

        profile_campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)