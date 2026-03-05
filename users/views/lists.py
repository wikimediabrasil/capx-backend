import requests
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.shortcuts import get_object_or_404
from users.models import Profile, Language, Badge
from skills.models import Skill
from users.serializers import UsersBySkillSerializer, UsersByTagSerializer, ProfileSerializer
from users.models import Territory, WikimediaProject
from orgs.models import Organization
from events.models import Events
from projects.models import Project
from CapX.useragent import get_user_agent

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"


class UsersBySkillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = UsersBySkillSerializer

    @extend_schema(
        summary='List users by skill.',
        description='Deprecated. This endpoint lists users by skill. Please use the /tags/ endpoint instead.',
        deprecated=True
    )
    def retrieve(self, request, *args, **kwargs):
        skill_id = self.kwargs['pk']
        skill = get_object_or_404(Skill, pk=skill_id)

        known_users = Profile.objects.filter(skills_known=skill)
        available_users = Profile.objects.filter(skills_available=skill)
        wanted_users = Profile.objects.filter(skills_wanted=skill)
        data = {
            'known': [{'id': user.id, 'display_name': user.display_name, 'username': user.user.username, 'avatar': user.avatar_id} for user in known_users],
            'available': [{'id': user.id, 'display_name': user.display_name, 'username': user.user.username, 'avatar': user.avatar_id} for user in available_users],
            'wanted': [{'id': user.id, 'display_name': user.display_name, 'username': user.user.username, 'avatar': user.avatar_id} for user in wanted_users],
        }
        return Response(data)

    @extend_schema(exclude=True)
    def list(self, request, *args, **kwargs):
        response = {'message': 'Please provide a skill id.'}
        return Response(response, status=status.HTTP_400_BAD_REQUEST)


class QuickListViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_url_kwarg = 'list_type'

    def get_queryset(self):
        list_type = self.kwargs.get('list_type')
        if list_type == 'language':
            return Language.objects.all()
        elif list_type == 'wikimedia_project':
            return WikimediaProject.objects.all()
        elif list_type == 'affiliation':
            return Organization.objects.all()
        elif list_type == 'territory':
            return Territory.objects.all()
        elif list_type == 'event':
            return Events.objects.all()
        elif list_type == 'project':
            return Project.objects.all()
        elif list_type == 'skills':
            return Skill.objects.all()
        elif list_type == 'badges':
            return Badge.objects.all()
        elif list_type == 'users':
            return Profile.objects.all()
        else:
            # Dummy empty queryset to avoid errors in the schema generation
            return Profile.objects.none()
    
    def get_serializer_class(self): # pragma: no cover
        # Dummy method to avoid errors in the schema generation
        return ProfileSerializer

    @extend_schema(
        summary='List all items in a simplified way.',
        description='This endpoint lists all items of a given type in a simplified way.',
        parameters=[
            OpenApiParameter(
                "list_type",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                required=True,
                description='The type of list to retrieve.',
                enum=['language', 'wikimedia_project', 'affiliation', 'territory', 'skills', 'event', 'project', 'badges', 'users'],
            ),
        ],
        responses={(200, 'application/json'): {
            'description': 'A mapping of item IDs to item names.',
            'type': 'object',
            'additionalProperties': {
                'type': 'string',
            },
            'example': {
                '1': 'Label 1',
                '2': 'Label 2',
                '3': 'Label 3',
            },
        }},
    )
    def retrieve(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = {item.id: str(item) for item in queryset}
        return Response(data)

    @extend_schema(
        exclude=True
    )
    def list(self, request, *args, **kwargs):
        return Response({'message': 'Please provide a valid list type.'}, status=status.HTTP_400_BAD_REQUEST)


class UsersByTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = UsersByTagSerializer

    @extend_schema(
        summary='Lists users by tag.',
        description='This endpoint retrieves users by tag.',
        parameters=[
            OpenApiParameter(
                "tag_type",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                required=True,
                description='The type of tag to search for.',
                enum=['skill_known', 'skill_available', 'skill_wanted', 'language', 'territory', 'wikimedia_project', 'affiliation'],
            ),
            OpenApiParameter(
                "tag_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
                required=True,
                description='The ID of the tag to search for.',
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        tag_type = kwargs.get('tag_type')
        tag_id = kwargs.get('tag_id')
        if not tag_type or not tag_id:
            return Response({'message': 'Please provide a valid tag type and tag ID.'}, status=status.HTTP_400_BAD_REQUEST)

        if tag_type == 'skill_known':
            queryset = Profile.objects.filter(skills_known__id=tag_id)
        elif tag_type == 'skill_available':
            queryset = Profile.objects.filter(skills_available__id=tag_id)
        elif tag_type == 'skill_wanted':
            queryset = Profile.objects.filter(skills_wanted__id=tag_id)
        elif tag_type == 'language':
            queryset = Profile.objects.filter(languageproficiency__language__id=tag_id)
        elif tag_type == 'territory':
            queryset = Profile.objects.filter(territory__id=tag_id)
        elif tag_type == 'wikimedia_project':
            queryset = Profile.objects.filter(wikimedia_project__id=tag_id)
        elif tag_type == 'affiliation':
            queryset = Profile.objects.filter(affiliation__id=tag_id)
        else:
            return Response({'message': 'Invalid tag type. Options are: skill_known, skill_available, skill_wanted, language, territory, wikimedia_project, affiliation.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(queryset, many=True).data)


class LanguageNamesView(APIView):
    """
    Returns all language names translated into a specific language using Wikidata.
    Falls back to the stored autonym, then the English name, if Wikidata has no label.
    """

    @extend_schema(
        summary='Get language names in a specific language',
        description='Returns all available languages with their names translated into the requested language. '
                    'Uses the Wikidata SPARQL endpoint to fetch translated names. '
                    'Falls back to the stored autonym, then the English name, when no Wikidata label is found.',
        parameters=[
            OpenApiParameter(
                'language_code',
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                required=True,
                description='BCP47 / ISO 639-1 code of the target language (e.g. "pt", "fr", "pt-br").',
            ),
        ],
        responses={(200, 'application/json'): {
            'description': 'Mapping of language IDs to their names in the requested language.',
            'type': 'object',
            'additionalProperties': {'type': 'string'},
            'example': {'1': 'Inglês', '2': 'Português', '3': 'Espanhol'},
        }},
    )
    def get(self, request, *args, **kwargs):
        language_code = self.kwargs.get('language_code')
        cache_key = f'language_names_{language_code}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        languages = list(Language.objects.all())
        if not languages:
            return Response({})

        codes = [lang.language_code for lang in languages]
        wikidata_labels = self._fetch_wikidata_labels(codes, language_code)
        english_labels = (
            wikidata_labels
            if language_code == 'en'
            else self._fetch_wikidata_labels(codes, 'en')
        )

        result = {}
        for lang in languages:
            label = (
                wikidata_labels.get(lang.language_code)
                or english_labels.get(lang.language_code)
                or lang.language_name
            )
            result[lang.id] = label

        cache.set(cache_key, result, 60 * 60 * 24)  # 24 hours
        return Response(result)

    @staticmethod
    def _to_bcp47(code):
        """Normalize a MediaWiki-style language code to standard BCP 47 capitalization.

        Rules: language subtag → lowercase, script subtag (4 alpha chars) → Title case,
        region subtag (2 alpha or 3 digit) → UPPERCASE.
        Examples: "pt-br" → "pt-BR", "zh-hans" → "zh-Hans", "sh-cyrl" → "sh-Cyrl".
        """
        parts = code.split('-')
        result = [parts[0].lower()]
        for part in parts[1:]:
            if len(part) == 4 and part.isalpha():
                result.append(part.title())  # Script subtag: Hans, Hant, Cyrl, Latn, Arab
            else:
                result.append(part.upper())  # Region subtag: BR, CN, TW
        return '-'.join(result)

    def _fetch_wikidata_labels(self, codes, target_lang):
        """Query Wikidata SPARQL for labels of the given language codes in target_lang.

        Matches codes against P218 (ISO 639-1) and P305 (IETF BCP 47).
        Normalizes codes to standard BCP 47 capitalization before querying (e.g. "pt-br"
        → "pt-BR") since Wikidata P305 values are case-sensitive.
        Returns a {original_code: label} dict; missing codes are simply absent.
        """
        # Build normalized BCP 47 codes and a reverse map bcp47 → original
        bcp47_to_original = {}
        for code in codes:
            bcp47 = self._to_bcp47(code)
            bcp47_to_original[bcp47] = code

        values = ' '.join(f'"{c}"' for c in bcp47_to_original.keys())
        normalized_target = self._to_bcp47(target_lang)
        query = f"""
SELECT ?code (SAMPLE(?label) AS ?label) WHERE {{
  VALUES ?code {{ {values} }}
  {{
    ?item wdt:P218 ?code .
  }} UNION {{
    ?item wdt:P305 ?code .
  }}
  ?item rdfs:label ?label .
  FILTER(LANG(?label) = "{normalized_target}")
}}
GROUP BY ?code
"""
        headers = {
            'Accept': 'application/sparql-results+json',
            'User-Agent': get_user_agent('LanguageNames'),
        }
        try:
            resp = requests.get(
                WIKIDATA_SPARQL_ENDPOINT,
                params={'query': query},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return {}

        labels = {}
        for binding in data.get('results', {}).get('bindings', []):
            bcp47_code = binding.get('code', {}).get('value', '')
            label = binding.get('label', {}).get('value', '')
            if bcp47_code and label:
                original = bcp47_to_original.get(bcp47_code, bcp47_code)
                labels[original] = label
        return labels
