import secrets
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from skills.models import Skill
from translate.models import MetabaseOAuthRequest, MetabaseOAuthToken
from translate.serializers import CapacityItemSerializer
from users.models import CustomUser


class TestCapacityTranslationViewSet(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser', password=str(secrets.randbits(16))
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch('translate.views_api.build_capacity_list')
    @patch('translate.views_api.MetabaseClient')
    def test_list_success(self, mock_client_cls, mock_build_capacity):
        Skill.objects.create(skill_wikidata_item='Q1')
        mock_client = mock_client_cls.return_value
        mock_client.fetch_map_and_terms.return_value = {
            'Q1': {'en': {'label': 'English', 'description': 'Desc', 'metabase_id': 'Q10'}}
        }
        mock_build_capacity.return_value = [
            {
                'qid': 'Q1',
                'metabase_id': 'Q10',
                'lang': 'es',
                'label': 'Hola',
                'description': 'Hola desc',
                'fallback_label': 'English',
                'fallback_description': 'Desc',
            }
        ]

        response = self.client.get('/translating/?lang=es&fallback=en')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serializer = CapacityItemSerializer(mock_build_capacity.return_value, many=True)
        self.assertEqual(response.data['results'], serializer.data)
        mock_client.fetch_map_and_terms.assert_called_once()

    def test_list_missing_lang(self):
        response = self.client.get('/translating/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing lang parameter', response.data['detail'])

    @patch('translate.views_api.MetabaseClient')
    def test_suggestions_empty(self, mock_client_cls):
        response = self.client.get('/translating/suggestions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'languages': [], 'stats': {}})
        mock_client_cls.return_value.fetch_map_and_terms.assert_called_once_with([])

    @patch('translate.views_api.MetabaseClient')
    def test_suggestions_stats(self, mock_client_cls):
        Skill.objects.create(skill_wikidata_item='Q1')
        Skill.objects.create(skill_wikidata_item='Q2')
        mock_client = mock_client_cls.return_value
        mock_client.fetch_map_and_terms.return_value = {
            'Q1': {
                'en': {'label': 'Label1', 'description': 'Desc1', 'metabase_id': 'Q10'},
                'es': {'label': 'Hola', 'description': 'Desc ES', 'metabase_id': 'Q10'},
            },
            'Q2': {
                'en': {'label': 'Label2', 'description': 'Desc2', 'metabase_id': 'Q11'},
                'es': {'label': 'Adios', 'description': 'Desc ES2', 'metabase_id': 'Q11'},
            },
        }

        # Test with an invalid min_completion, should be treated as 0.8
        response = self.client.get('/translating/suggestions/?min_completion=foo')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['languages'], ['es'])
        self.assertIn('stats', response.data)
        self.assertIn('es', response.data['stats'])
        self.assertAlmostEqual(response.data['stats']['es']['completion'], 1.0)



    @patch('translate.views_api.requests.get')
    def test_languages_success(self, mock_get):
        paraminfo_response = MagicMock()
        paraminfo_response.json.return_value = {
            'paraminfo': {
                'modules': [
                    {
                        'name': 'wbsetlabel',
                        'parameters': [
                            {
                                'name': 'language',
                                'type': ['en', 'es'],
                            }
                        ],
                    }
                ]
            }
        }
        paraminfo_response.raise_for_status = MagicMock()

        languageinfo_response = MagicMock()
        languageinfo_response.json.return_value = {
            'query': {
                'languageinfo': {
                    'en': {'name': 'English', 'autonym': 'English'},
                    'es': {'name': 'Spanish', 'autonym': 'Espanol'},
                }
            }
        }
        languageinfo_response.raise_for_status = MagicMock()

        mock_get.side_effect = [paraminfo_response, languageinfo_response]

        response = self.client.get('/translating/languages/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = [
            {'code': 'en', 'name': 'English', 'autonym': 'English', 'label': 'en — English'},
            {'code': 'es', 'name': 'Spanish', 'autonym': 'Espanol', 'label': 'es — Spanish — Espanol'},
        ]
        self.assertEqual(response.data['languages'], expected)

    @patch('translate.views_api.requests.get')
    def test_languages_error(self, mock_get):
        mock_get.side_effect = Exception('network down')

        response = self.client.get('/translating/languages/')

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('Failed to fetch languages', response.data['detail'])

    def test_create_invalid_serializer(self):
        response = self.client.post('/translating/', data={}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    @patch('translate.views_api.MetabaseClient')
    def test_create_metabase_item_not_found(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.fetch_map_and_terms.return_value = {}

        payload = {'qid': 'Q1', 'lang': 'es', 'label': 'Hola'}
        response = self.client.post('/translating/', data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Metabase item not found', response.data['detail'])

    @patch('translate.views_api.MetabaseClient')
    def test_create_needs_confirmation(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.fetch_map_and_terms.return_value = {
            'Q1': {'en': {'metabase_id': 'Q10', 'label': 'English', 'description': 'Desc'}}
        }
        mock_client.login_bot.return_value = None
        mock_client.set_term.side_effect = RuntimeError('You must confirm your email address')

        payload = {'qid': 'Q1', 'lang': 'es', 'label': 'Hola'}
        response = self.client.post('/translating/', data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('confirm', response.data['detail'])

    @patch('translate.views_api.MetabaseClient')
    def test_create_description_too_long(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.fetch_map_and_terms.return_value = {
            'Q1': {'en': {'metabase_id': 'Q10', 'label': 'English', 'description': 'Desc'}}
        }
        mock_client.login_bot.return_value = None
        mock_client.set_term.side_effect = RuntimeError('Description must be no more than 200 characters')

        payload = {'qid': 'Q1', 'lang': 'es', 'description': 'x' * 201}
        response = self.client.post('/translating/', data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['field'], 'description')
        self.assertEqual(response.data['max_length'], 200)

    @patch('translate.views_api.MetabaseClient')
    def test_create_provider_error(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.fetch_map_and_terms.return_value = {
            'Q1': {'en': {'metabase_id': 'Q10', 'label': 'English', 'description': 'Desc'}}
        }
        mock_client.login_bot.return_value = None
        mock_client.set_term.side_effect = RuntimeError('boom')

        payload = {'qid': 'Q1', 'lang': 'es', 'label': 'Hola'}
        response = self.client.post('/translating/', data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('Failed to submit to Metabase: boom', response.data['detail'])

    @patch('translate.views_api.MetabaseClient')
    def test_create_success_with_token(self, mock_client_cls):
        MetabaseOAuthToken.objects.create(
            user=self.user, access_token='tok', access_secret='sec', mb_username='mbuser'
        )
        mock_client = mock_client_cls.return_value
        mock_client.fetch_map_and_terms.return_value = {
            'Q1': {'en': {'metabase_id': 'Q10', 'label': 'English', 'description': 'Desc'}}
        }
        payload = {'qid': 'Q1', 'lang': 'es', 'label': 'Hola', 'description': 'Desc ES'}

        response = self.client.post('/translating/', data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['changed'], ['label', 'description'])
        self.assertEqual(response.data['metabase_id'], 'Q10')
        mock_client.login_user_oauth.assert_called_once_with('tok', 'sec')


class TestCapacityTranslationOauthViewSet(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='oauthuser', password=str(secrets.randbits(16))
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch.dict('os.environ', {}, clear=True)
    def test_begin_missing_config(self):
        response = self.client.post('/translating_oauth/begin/')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('not configured', response.data['detail'])

    @patch.dict(
        'os.environ',
        {'METABASE_OAUTH_CONSUMER_KEY': 'key', 'METABASE_OAUTH_CONSUMER_SECRET': 'secret'},
        clear=True,
    )
    @patch('translate.views_api.OAuth1Session')
    def test_begin_success(self, mock_oauth_cls):
        mock_oauth = mock_oauth_cls.return_value
        mock_oauth.fetch_request_token.return_value = {
            'oauth_token': 'req',
            'oauth_token_secret': 'secret',
        }

        response = self.client.post('/translating_oauth/begin/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('state', response.data)
        state = response.data['state']
        self.assertTrue(
            response.data['authorization_url'].endswith(f'/translate/metabase/authorize/{state}/')
        )
        self.assertTrue(MetabaseOAuthRequest.objects.filter(state=state, user=self.user).exists())

    @patch.dict(
        'os.environ',
        {'METABASE_OAUTH_CONSUMER_KEY': 'key', 'METABASE_OAUTH_CONSUMER_SECRET': 'secret'},
        clear=True,
    )
    @patch('translate.views_api.OAuth1Session')
    def test_begin_provider_error(self, mock_oauth_cls):
        mock_oauth = mock_oauth_cls.return_value
        mock_oauth.fetch_request_token.side_effect = Exception('provider boom')

        response = self.client.post('/translating_oauth/begin/')

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('Failed to initiate OAuth', response.data['detail'])

    @patch.dict(
        'os.environ',
        {'METABASE_OAUTH_CONSUMER_KEY': 'key', 'METABASE_OAUTH_CONSUMER_SECRET': 'secret'},
        clear=True,
    )
    @patch('translate.views_api.OAuth1Session')
    def test_begin_tokens_not_in_response(self, mock_oauth_cls):
        mock_oauth = mock_oauth_cls.return_value
        mock_oauth.fetch_request_token.return_value = {}

        response = self.client.post('/translating_oauth/begin/')
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('Provider did not supply request token/secret.', response.data['detail'])

    def test_status_connected(self):
        MetabaseOAuthToken.objects.create(
            user=self.user, access_token='tok', access_secret='sec', mb_username='mbuser'
        )

        response = self.client.get('/translating_oauth/status/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['connected'])
        self.assertEqual(response.data['username'], 'mbuser')

    def test_disconnect(self):
        MetabaseOAuthToken.objects.create(
            user=self.user, access_token='tok', access_secret='sec', mb_username='mbuser'
        )

        response = self.client.delete('/translating_oauth/disconnect/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(MetabaseOAuthToken.objects.filter(user=self.user).exists())
