from typing import List

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from skills.models import Skill
from .services import MetabaseClient, build_capacity_list
from .models import MetabaseOAuthToken
from .serializers import CapacityItemSerializer, TranslationSubmitSerializer

from drf_spectacular.utils import extend_schema, OpenApiParameter


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
