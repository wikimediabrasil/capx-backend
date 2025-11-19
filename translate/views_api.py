from typing import List

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from skills.models import Skill
from .services import MetabaseClient, build_capacity_list


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def capacities_list(request):
    """Return list of capacities with current and fallback terms for a given lang.
    Query params:
      - lang: required language code (e.g., 'pt-br')
      - fallback: optional fallback language (default 'en')
    """
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
    # Sort by missing first to help translators
    def is_missing(it):
        return (not it.get('label')) or (not it.get('description'))
    items.sort(key=lambda it: (not is_missing(it), (it.get('fallback_label') or '') .lower()))
    return Response({'results': items})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_translation(request):
    """Submit label/description for a given qid/lang using the bot.
    Body (JSON): { qid: 'Q...', lang: 'xx', label?: str, description?: str }
    """
    payload = request.data or {}
    qid = (payload.get('qid') or '').strip()
    lang = (payload.get('lang') or '').strip()
    label = payload.get('label')
    description = payload.get('description')

    if not qid or not lang or (label is None and description is None):
        return Response({'detail': 'Missing qid, lang, or fields'}, status=status.HTTP_400_BAD_REQUEST)
    if lang == 'en':
        return Response({'detail': 'English (en) is the base language and cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)

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

    client.login_bot()
    changed = []
    if label is not None:
        client.set_term(metabase_id, lang, 'label', label, request.user.username)
        changed.append('label')
    if description is not None:
        client.set_term(metabase_id, lang, 'description', description, request.user.username)
        changed.append('description')

    return Response({'status': 'ok', 'changed': changed, 'metabase_id': metabase_id})
