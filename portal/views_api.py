from rest_framework import mixins, viewsets, permissions

from portal.models import (
    Partner,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMenteeResponse,
)
from portal.serializers import (
    PartnerSerializer,
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
    queryset = PartnerMentorshipFormMentor.objects.select_related('partner__organization').order_by('-created_at')
    serializer_class = PartnerMentorshipFormMentorSerializer

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
    queryset = PartnerMentorshipFormMentee.objects.select_related('partner__organization').order_by('-created_at')
    serializer_class = PartnerMentorshipFormMenteeSerializer

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
