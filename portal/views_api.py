from rest_framework import mixins, viewsets, permissions

from portal.models import (
    PartnerMentorshipAvailability,
    PartnerMentorshipFormMentor,
    PartnerMentorshipFormMentorResponse,
    PartnerMentorshipFormMentee,
    PartnerMentorshipFormMenteeResponse,
)
from portal.serializers import (
    PartnerMentorshipAvailabilitySerializer,
    PartnerMentorshipFormMentorSerializer,
    PartnerMentorshipFormMentorResponseSerializer,
    PartnerMentorshipFormMenteeSerializer,
    PartnerMentorshipFormMenteeResponseSerializer,
)

class PartnerMentorshipAvailabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PartnerMentorshipAvailability.objects.select_related('partner__organization').order_by('-updated_at')
    serializer_class = PartnerMentorshipAvailabilitySerializer


class PartnerMentorshipFormMentorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PartnerMentorshipFormMentor.objects.select_related('partner__organization').order_by('-created_at')
    serializer_class = PartnerMentorshipFormMentorSerializer


class PartnerMentorshipFormMenteeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PartnerMentorshipFormMentee.objects.select_related('partner__organization').order_by('-created_at')
    serializer_class = PartnerMentorshipFormMenteeSerializer


class PartnerMentorshipFormMentorResponseViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = PartnerMentorshipFormMentorResponse.objects.select_related(
        'form',
        'user',
    ).order_by('-created_at')
    serializer_class = PartnerMentorshipFormMentorResponseSerializer
    http_method_names = ['post']
    permission_classes = [permissions.IsAuthenticated]


class PartnerMentorshipFormMenteeResponseViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = PartnerMentorshipFormMenteeResponse.objects.select_related(
        'form',
        'user',
    ).order_by('-created_at')
    serializer_class = PartnerMentorshipFormMenteeResponseSerializer
    http_method_names = ['post']
    permission_classes = [permissions.IsAuthenticated]
