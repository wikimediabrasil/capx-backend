from .models import Message
from .serializers import MessageSerializer
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from requests_oauthlib import OAuth1Session
from django.conf import settings
from social_django.models import UserSocialAuth

@extend_schema_view(
    list=extend_schema(
        summary="List all messages.",
        description="This endpoint lists all messages sent by the user. If the user is a staff member, all messages are listed."
    ),
    create=extend_schema(
        summary="Create a new message.",
        description="This endpoint creates a new message."
    ),
    retrieve=extend_schema(
        summary="Retrieve a message.",
        description="This endpoint retrieves a message by its ID.",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)]
    )
)
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date']
    ordering = ['-date']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Message.objects.all()
        else:
            return Message.objects.filter(sender=user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        serializer_class.Meta.read_only_fields = ('sender',)
        return serializer_class

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(exclude=True)
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def _get_oauth_session(self, user):
        """Get OAuth session for a user"""
        try:
            user_social_auth = UserSocialAuth.objects.get(user=user)
            return OAuth1Session(
                settings.SOCIAL_AUTH_MEDIAWIKI_KEY,
                client_secret=settings.SOCIAL_AUTH_MEDIAWIKI_SECRET,
                resource_owner_key=user_social_auth.extra_data['access_token']['oauth_token'],
                resource_owner_secret=user_social_auth.extra_data['access_token']['oauth_token_secret']
            )
        except UserSocialAuth.DoesNotExist:
            return None

    def _check_user_emailable(self, username):
        """Check if a user is emailable via Wikimedia API"""
        try:
            oauth = self._get_oauth_session(self.request.user)
            if not oauth:
                return False

            url = 'https://meta.wikimedia.org/w/api.php'
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'users',
                'formatversion': '2',
                'usprop': 'emailable',
                'ususers': username,
            }
            response = oauth.get(url, params=params, timeout=60)
            return response.json().get('query', {}).get('users', [{}])[0].get('emailable', False)
        except Exception:
            return False

    @extend_schema(
        summary="Check if users can send/receive email",
        description="Verifies if both sender (authenticated user) and receiver can send/receive email via Wikimedia.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'receiver': {'type': 'string', 'description': 'Wikimedia username of the receiver'}
                },
                'required': ['receiver']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'sender_emailable': {'type': 'boolean'},
                    'receiver_emailable': {'type': 'boolean'},
                    'can_send_email': {'type': 'boolean'}
                }
            }
        }
    )
    @action(detail=False, methods=['post'])
    def check_emailable(self, request):
        """Check if sender and receiver can send/receive email"""
        receiver = request.data.get('receiver')

        if not receiver:
            return Response(
                {'error': 'receiver is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if sender (authenticated user) is emailable
        sender_emailable = self._check_user_emailable(request.user.username)

        # Check if receiver is emailable
        receiver_emailable = self._check_user_emailable(receiver)

        return Response({
            'sender_emailable': sender_emailable,
            'receiver_emailable': receiver_emailable,
            'can_send_email': sender_emailable and receiver_emailable
        })