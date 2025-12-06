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
import requests


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
        summary='List allowed languages (Wikibase)',
        description='Returns allowed language codes for wbsetlabel, enriched with name and autonym.',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'languages': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'code': {'type': 'string'},
                                'name': {'type': 'string'},
                                'autonym': {'type': 'string'},
                                'label': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='languages')
    def languages(self, request):
        try:
            pi = requests.get(
                'https://metabase.wikibase.cloud/w/api.php',
                params={'action': 'paraminfo', 'format': 'json', 'modules': 'wbsetlabel'},
                timeout=30
            )
            pi.raise_for_status()
            pi_data = pi.json()
            modules = (pi_data.get('paraminfo', {}) or {}).get('modules', [])
            mod = next((m for m in modules if m.get('name') == 'wbsetlabel'), None)
            params_list = mod.get('parameters', []) if mod else []
            lang_param = next((p for p in params_list if p.get('name') == 'language'), None)
            codes = lang_param.get('type', []) if lang_param else []

            li = requests.get(
                'https://metabase.wikibase.cloud/w/api.php',
                params={'action': 'query', 'format': 'json', 'meta': 'languageinfo', 'liprop': 'autonym|name', 'uselang': 'en'},
                timeout=30
            )
            li.raise_for_status()
            li_data = li.json()
            info = (li_data.get('query', {}) or {}).get('languageinfo', {})

            def build_entry(code: str):
                meta = info.get(code, {}) or {}
                name = meta.get('name') or code
                autonym = meta.get('autonym') or ''
                # label: English name + code, and autonym when different
                label = f"{code} — {name}"
                if autonym and autonym != name:
                    label = f"{code} — {name} — {autonym}"
                return {'code': code, 'name': name, 'autonym': autonym, 'label': label}

            entries = [build_entry(c) for c in codes]
            entries.sort(key=lambda x: (x['code']))
            return Response({'languages': entries})
        except Exception as e:
            return Response({'detail': f'Failed to fetch languages: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

    @extend_schema(
        summary='Suggest languages by completion',
        description='Returns language codes with >= min_completion ratio of items having both label and description.',
        parameters=[
            OpenApiParameter(
                name='min_completion',
                type=float,
                description='Minimum completion ratio (0-1). Default: 0.8',
                required=False,
            ),
        ],
        responses={
            '200': {
                'type': 'object', 
                'properties': {
                    'languages': {
                        'type': 'array', 
                        'items': {
                            'type': 'string'
                        }
                    }, 
                    'stats': {
                        'type': 'object', 
                        'properties': {
                            'complete': {'type': 'number'}, 
                            'total': {'type': 'number'}, 
                            'completion': {'type': 'number'}
                        }
                    }, 
                    'min_completion': {
                        'type': 'number'
                    }
                }
            }
        },
    )
    @action(detail=False, methods=['get'], url_path='suggestions')
    def suggestions(self, request):
        # Compute per-language completeness across all capacity items
        try:
            min_completion = float(request.query_params.get('min_completion', '0.8'))
        except ValueError:
            min_completion = 0.8
        min_completion = max(0.0, min(1.0, min_completion))

        qids: List[str] = list(
            Skill.objects.order_by('pk').values_list('skill_wikidata_item', flat=True)
        )
        client = MetabaseClient()
        terms = client.fetch_map_and_terms(qids)

        total = len(qids) if qids else 0
        if total == 0:
            return Response({'languages': [], 'stats': {}}, status=status.HTTP_200_OK)

        # Aggregate completeness: label AND description present for the language
        counts = {}
        for qid, lang_map in terms.items():
            for lg, entry in lang_map.items():
                has_label = bool(entry.get('label'))
                has_desc = bool(entry.get('description'))
                if has_label and has_desc:
                    counts[lg] = counts.get(lg, 0) + 1

        stats = {}
        for lg, cnt in counts.items():
            completion = cnt / total
            stats[lg] = {'complete': cnt, 'total': total, 'completion': completion}

        languages = [lg for lg, s in stats.items() if s['completion'] >= min_completion and lg != 'en']
        languages.sort()
        return Response({'languages': languages, 'stats': stats, 'min_completion': min_completion}, status=status.HTTP_200_OK)

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
        try:
            if label is not None:
                client.set_term(metabase_id, lang, 'label', label, request.user.username)
                changed.append('label')
            if description is not None:
                client.set_term(metabase_id, lang, 'description', description, request.user.username)
                changed.append('description')
        except Exception as e:
            # Provide a friendly message when Metabase/Wikibase denies edits due to unconfirmed email
            msg = str(e)
            needs_confirmation = ('confirmedittext' in msg) or ('You must confirm your email address' in msg)
            permission_denied = ('permissiondenied' in msg) or ('You do not have the permissions needed' in msg)
            too_long = ('wikibase-validator-description-too-long' in msg) or ('Description must be no more than' in msg)
            if needs_confirmation or permission_denied:
                return Response(
                    {
                        'detail': (
                            'Your Metabase account must confirm its email before editing. '
                            'Please open Metabase Preferences and validate your email: '
                            'https://metabase.wikibase.cloud/wiki/Special:Preferences'
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            if too_long:
                # Try to extract the limit number from the message
                limit = None
                for part in msg.split():
                    if part.isdigit():
                        limit = part
                        break
                limit_text = limit or '250'
                return Response(
                    {
                        'detail': f'Description is too long. Maximum length is {limit_text} characters.',
                        'field': 'description',
                        'max_length': int(limit_text) if limit_text.isdigit() else 250,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Fallback: bubble up as a generic bad gateway from provider
            return Response({'detail': f'Failed to submit to Metabase: {msg}'}, status=status.HTTP_502_BAD_GATEWAY)

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
