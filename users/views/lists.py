import requests, re
from django.core.cache import cache
from babel import Locale, UnknownLocaleError
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

MEDIAWIKI_LOCALNAMES_RAW_BASE = "https://raw.githubusercontent.com/wikimedia/mediawiki-extensions-cldr/master/LocalNames"


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
        description='This endpoint lists all items of a given type in a simplified way. '
                    'For list_type=language, you can pass ?lang=<code> to return translated '
                    'names using CLDR plus MediaWiki LocalNames overrides.',
        parameters=[
            OpenApiParameter(
                "list_type",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                required=True,
                description='The type of list to retrieve.',
                enum=['language', 'wikimedia_project', 'affiliation', 'territory', 'skills', 'event', 'project', 'badges', 'users'],
            ),
            OpenApiParameter(
                'lang',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=False,
                description='Only used when list_type=language. BCP47 / ISO 639-1 code of the target language (e.g. "pt", "fr", "pt-br").',
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
        if self.kwargs.get('list_type') == 'language':
            language_code = request.query_params.get('lang')
            if language_code:
                return Response(self._get_translated_language_names(language_code))

        queryset = self.get_queryset()
        data = {item.id: str(item) for item in queryset}
        return Response(data)

    def _get_translated_language_names(self, language_code):
        cache_key = f'language_names_{language_code}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        languages = list(Language.objects.all())
        if not languages:
            return {}

        codes = [lang.language_code for lang in languages]
        try:
            cldr_labels = self._fetch_cldr_labels(codes, language_code)
        except Exception:
            cldr_labels = {}

        try:
            localnames_labels = self._fetch_localnames_labels(language_code)
        except Exception:
            localnames_labels = {}

        result = {}
        for lang in languages:
            normalized_code = (lang.language_code or '').lower()
            label = (
                localnames_labels.get(normalized_code)
                or cldr_labels.get(normalized_code)
                or lang.language_autonym
                or lang.language_name
            )
            result[lang.id] = label

        cache.set(cache_key, result, 60 * 60 * 24)  # 24 hours
        return result

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

    @staticmethod
    def _to_babel_locale(code):
        return QuickListViewSet._to_bcp47(code).replace('-', '_')

    @staticmethod
    def _to_mediawiki_localnames_file(code):
        normalized = code.lower().replace('_', '-')
        parts = normalized.split('-')
        first = parts[0].capitalize() if parts and parts[0] else ''
        suffix = ''.join(f'_{part}' for part in parts[1:])
        return f'LocalNames{first}{suffix}.php'

    @staticmethod
    def _extract_localnames_map(php_text):

        start = php_text.find('$languageNames = [')
        if start == -1:
            return {}

        end = php_text.find('];', start)
        if end == -1:
            return {}

        body = php_text[start:end]
        pattern = re.compile(r"'([^']+)'\s*=>\s*'((?:\\\\'|[^'])*)'", re.DOTALL)

        result = {}
        for code, label in pattern.findall(body):
            clean_label = label.replace("\\'", "'").replace('\\\\', '\\')
            if code and clean_label:
                result[code.lower()] = clean_label
        return result

    def _fetch_cldr_labels(self, codes, target_lang):
        """Resolve language labels from CLDR (Babel) for target_lang."""
        labels = {}

        normalized_target = self._to_babel_locale(target_lang)
        target_candidates = [normalized_target]
        if '_' in normalized_target:
            target_candidates.append(normalized_target.split('_', 1)[0])

        target_locales = []
        for candidate in target_candidates:
            try:
                target_locales.append(Locale.parse(candidate, sep='_'))
            except (UnknownLocaleError, ValueError):
                continue

        if not target_locales:
            return labels

        for code in codes:
            normalized_code = self._to_babel_locale(code)
            primary_code = normalized_code.split('_', 1)[0].lower()

            label = None
            for target_locale in target_locales:
                try:
                    lang_locale = Locale.parse(normalized_code, sep='_')
                    label = lang_locale.get_display_name(target_locale)
                except (UnknownLocaleError, ValueError):
                    label = target_locale.languages.get(primary_code)

                if label:
                    break

            if label:
                labels[code.lower()] = label

        return labels

    def _fetch_localnames_labels(self, target_lang):
        """Fetch LocalNames overrides from Wikimedia CLDR extension repository."""
        file_name = self._to_mediawiki_localnames_file(target_lang)
        url = f'{MEDIAWIKI_LOCALNAMES_RAW_BASE}/{file_name}'
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 404 and '-' in target_lang:
                primary = target_lang.split('-', 1)[0]
                fallback_file = self._to_mediawiki_localnames_file(primary)
                fallback_url = f'{MEDIAWIKI_LOCALNAMES_RAW_BASE}/{fallback_file}'
                response = requests.get(fallback_url, timeout=10)

            response.raise_for_status()
            return self._extract_localnames_map(response.text)
        except Exception:
            return {}

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


