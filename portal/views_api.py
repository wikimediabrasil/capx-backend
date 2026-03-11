from rest_framework import mixins, viewsets, permissions

from portal.models import (
    Partner,
    PartnerMentorshipSettings,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMenteeResponse,
)
from portal.serializers import (
    PartnerSerializer,
    PartnerSettingsSerializer,
    PartnerMentorshipFormMentorSerializer,
    PartnerMentorshipFormMentorResponseSerializer,
    PartnerMentorshipFormMenteeSerializer,
    PartnerMentorshipFormMenteeResponseSerializer,
)

from drf_spectacular.utils import extend_schema_view, extend_schema

@extend_schema_view(
    list=extend_schema(
        summary='List partners.',
        description='This endpoint lists all partners.',
    ),
    retrieve=extend_schema(
        summary='Retrieve partner by the organization ID.',
        description='This endpoint retrieves a partner by the organization ID.',
    ),
)
class PartnerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Partner.objects.select_related('organization').order_by('-created_at')
    serializer_class = PartnerSerializer
    lookup_field = 'organization_id'


@extend_schema_view(
    list=extend_schema(
        summary='List mentorship settings for partners.',
        description='This endpoint lists all mentorship settings for partners.',
    ),
    retrieve=extend_schema(
        summary='Retrieve mentorship settings for a partner by the organization ID.',
        description='This endpoint retrieves mentorship settings for a partner by the organization ID.',
    ),
)
class PartnerSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PartnerMentorshipSettings.objects.select_related('partner__organization').prefetch_related('skills', 'languages').order_by('-created_at')
    serializer_class = PartnerSettingsSerializer
    lookup_field = 'partner__organization_id'


@extend_schema_view(
    list=extend_schema(
        summary='List mentorship forms for mentors.',
        description='This endpoint lists all mentorship forms for mentors.',
    ),
    retrieve=extend_schema(
        summary='Retrieve mentorship form for mentors by ID.',
        description='This endpoint retrieves a mentorship form for mentors by its ID.',
    ),
)
class PartnerMentorshipFormMentorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PartnerMentorshipFormMentorSerializer

    def get_queryset(self):
        queryset = PartnerMentorshipFormMentor.objects.select_related('partner__organization').order_by('-created_at', '-id')

        if self.action == 'list':
            return queryset[:1] # Return only the most recent form for listing

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary='List mentorship forms for mentees.',
        description='This endpoint lists all mentorship forms for mentees.',
    ),
    retrieve=extend_schema(
        summary='Retrieve mentorship form for mentees by ID.',
        description='This endpoint retrieves a mentorship form for mentees by its ID.',
    ),
)
class PartnerMentorshipFormMenteeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PartnerMentorshipFormMenteeSerializer

    def get_queryset(self):
        queryset = PartnerMentorshipFormMentee.objects.select_related('partner__organization').order_by('-created_at', '-id')

        if self.action == 'list':
            return queryset[:1] # Return only the most recent form for listing

        return queryset

@extend_schema_view(
    create=extend_schema(
        summary='Submit a mentorship form response for mentors.',
        description='This endpoint allows authenticated users to submit a mentorship form response for mentors.',
    ),
)
class PartnerMentorshipFormMentorResponseViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = PartnerMentorshipFormMentorResponse.objects.select_related(
        'form',
        'user',
    ).order_by('-created_at')
    serializer_class = PartnerMentorshipFormMentorResponseSerializer
    http_method_names = ['post']
    permission_classes = [permissions.IsAuthenticated]

@extend_schema_view(
    create=extend_schema(
        summary='Submit a mentorship form response for mentees.',
        description='This endpoint allows authenticated users to submit a mentorship form response for mentees.',
    ),
)
class PartnerMentorshipFormMenteeResponseViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = PartnerMentorshipFormMenteeResponse.objects.select_related(
        'form',
        'user',
    ).order_by('-created_at')
    serializer_class = PartnerMentorshipFormMenteeResponseSerializer
    http_method_names = ['post']
    permission_classes = [permissions.IsAuthenticated]
