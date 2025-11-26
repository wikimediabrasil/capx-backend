from typing import List
import os

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from skills.models import Skill
from .services import MetabaseClient, build_capacity_list
from .models import MetabaseOAuthToken, MetabaseOAuthRequest
from .serializers import CapacityItemSerializer, TranslationSubmitSerializer, OauthBeginSerializer, OauthStatusSerializer, OauthDisconnectSerializer

from drf_spectacular.utils import extend_schema, OpenApiParameter
from requests_oauthlib import OAuth1Session
from django.urls import reverse
from django.utils import timezone


class CapacityTranslationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List capacity items with translations.',
        description='This endpoint lists capacity items with their translations retrieved from Metabase.',
        parameters=[
            OpenApiParameter(
                name='lang',
                type=str,
                description='Target language code (e.g., "fr" for French).',
                required=True,
            ),
            OpenApiParameter(
                name='fallback',
                type=str,
                description='Fallback language code (default: "en").',
                required=False,
            ),
        ],
        responses=CapacityItemSerializer,
    )
    def list(self, request):  # GET /capacities/?lang=xx&fallback=en
        lang = request.query_params.get('lang')
        if not lang:
            return Response({'detail': 'Missing lang parameter'}, status=status.HTTP_400_BAD_REQUEST)
        fallback = request.query_params.get('fallback', 'en')

        qids: List[str] = list(
            Skill.objects.order_by('pk').values_list('skill_wikidata_item', flat=True)
        )
        client = MetabaseClient()
        terms = client.fetch_map_and_terms(qids)
        items = build_capacity_list(terms, lang=lang, fallback=fallback)

        def is_missing(it):
            return (not it.get('label')) or (not it.get('description'))

        items.sort(key=lambda it: (not is_missing(it), (it.get('fallback_label') or '').lower()))
        serializer = CapacityItemSerializer(items, many=True)
        return Response({'results': serializer.data})

    @extend_schema(
        summary='Submit a translation for a capacity item.',
        description='This endpoint allows submitting translations for capacity items to Metabase.',
        request=TranslationSubmitSerializer,
        responses={'200': {'type': 'object', 'properties': {'status': {'type': 'string'}, 'changed': {'type': 'array', 'items': {'type': 'string'}}, 'metabase_id': {'type': 'string'}}}},
    )
    def create(self, request):  # POST /capacities/
        serializer = TranslationSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        qid = serializer.validated_data['qid']
        lang = serializer.validated_data['lang']
        label = serializer.validated_data.get('label')
        description = serializer.validated_data.get('description')

        client = MetabaseClient()
        mapping = client.fetch_map_and_terms([qid])
        item = mapping.get(qid, {})
        metabase_id = None
        for lang_map in item.values():
            metabase_id = lang_map.get('metabase_id')
            if metabase_id:
                break
        if not metabase_id:
            return Response({'detail': 'Metabase item not found for qid'}, status=status.HTTP_400_BAD_REQUEST)

        # Prefer per-user OAuth if connected; fallback to bot
        token_obj = MetabaseOAuthToken.objects.filter(user=request.user).first()
        if token_obj:
            client.login_user_oauth(token_obj.access_token, token_obj.access_secret)
        else:
            client.login_bot()
        changed = []
        if label is not None:
            client.set_term(metabase_id, lang, 'label', label, request.user.username)
            changed.append('label')
        if description is not None:
            client.set_term(metabase_id, lang, 'description', description, request.user.username)
            changed.append('description')

        return Response({'status': 'ok', 'changed': changed, 'metabase_id': metabase_id})


class CapacityTranslationOauthViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    REQUEST_TOKEN_URL = 'https://metabase.wikibase.cloud/w/index.php?title=Special:OAuth/initiate'
    AUTHORIZE_URL = 'https://metabase.wikibase.cloud/w/index.php?title=Special:OAuth/authorize'
    
    @extend_schema(
        summary='Begin Metabase OAuth (popup-friendly)',
        description='Stores temporary request credentials in session and returns a local URL to redirect the user. That local URL will redirect to Metabase authorize.',
        request=None,
        responses=OauthBeginSerializer,
    )
    @action(detail=False, methods=['post'], url_path='begin')
    def begin(self, request):
        # Verify consumer credentials
        consumer_key = os.environ.get('METABASE_OAUTH_CONSUMER_KEY')
        consumer_secret = os.environ.get('METABASE_OAUTH_CONSUMER_SECRET')
        if not consumer_key or not consumer_secret:
            return Response({'detail': 'Metabase OAuth is not configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Initiate OAuth request
        oauth = OAuth1Session(client_key=consumer_key, client_secret=consumer_secret, callback_uri="oob")
        try:
            fetch_response = oauth.fetch_request_token(self.REQUEST_TOKEN_URL)
        except Exception as e:
            return Response({'detail': f'Failed to initiate OAuth: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

        # Extract tokens
        request_token = fetch_response.get('oauth_token')
        request_secret = fetch_response.get('oauth_token_secret')
        if not request_token or not request_secret:
            return Response({'detail': 'Provider did not supply request token/secret.'}, status=status.HTTP_502_BAD_GATEWAY)

        # Opportunistic cleanup of stale requests
        MetabaseOAuthRequest.objects.filter(consumed=False).exclude(created_at__gte=timezone.now()-timezone.timedelta(minutes=15)).delete()

        # Store request info and build local authorization URL
        oreq = MetabaseOAuthRequest.objects.create(user=request.user, request_token=request_token, request_secret=request_secret)
        local_url = request.build_absolute_uri(reverse('translate:metabase_oauth_authorize_state', args=[oreq.state]))
        return Response({'authorization_url': local_url, 'state': oreq.state})

    @extend_schema(
        summary='Metabase OAuth status for current user',
        description='Returns whether the current user has a connected Metabase account.',
        request=None,
        responses=OauthStatusSerializer,
    )
    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        tok = MetabaseOAuthToken.objects.filter(user=request.user).first()
        return Response({'connected': bool(tok), 'username': getattr(tok, 'mb_username', None) or ''})

    @extend_schema(
        summary='Disconnect Metabase OAuth',
        description='Revokes local stored tokens (does not revoke at provider).',
        request=None,
        responses=OauthDisconnectSerializer,
    )
    @action(detail=False, methods=['delete'], url_path='disconnect')
    def disconnect(self, request):
        MetabaseOAuthToken.objects.filter(user=request.user).delete()
        return Response({'status': 'ok'})
