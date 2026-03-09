import json
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from translate.services import MetabaseClient, build_capacity_list

class TestMetabaseClient(TestCase):
    
    @patch.dict('os.environ', {'METABASE_USERNAME': 'testuser', 'METABASE_PASSWORD': 'testpass'}, clear=True)
    @patch('translate.services.requests.Session')
    def test_login_bot_success(self, mock_session_class):
        # Cria um mock para a sessão HTTP (requests.Session)
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Cria mocks para as respostas dos métodos GET e POST
        mock_get_response = MagicMock()
        mock_post_response = MagicMock()

        # O método .json() do GET retorna primeiro o logintoken, depois o csrftoken
        mock_get_response.json.side_effect = [
            {"query": {"tokens": {"logintoken": "test_token"}}},
            {"query": {"tokens": {"csrftoken": "csrf_token"}}},
        ]

        # O método .json() do POST retorna sucesso no login
        mock_post_response.json.return_value = {"login": {"result": "Success"}}

        # Os métodos .get() e .post() da sessão retornam os mocks configurados acima
        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        # Cria o cliente e executa o login_bot (usando os mocks acima)
        client = MetabaseClient()
        result = client.login_bot()

        # Verifica se o método retorna o próprio cliente e se os atributos foram configurados corretamente
        assert result is client
        assert client._token == "csrf_token"
        assert client._session is not None

    @patch.dict('os.environ', {'METABASE_USERNAME': 'testuser', 'METABASE_PASSWORD': 'testpass'}, clear=True)
    @patch('translate.services.requests.Session')
    def test_login_bot_login_token_failure(self, mock_session_class):
        # Simula retorno sem logintoken para cobrir raise em _mw_login
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {"query": {"tokens": {}}}
        mock_get_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_get_response

        client = MetabaseClient()
        with self.assertRaisesRegex(RuntimeError, r"Failed to get login token\."):
            client.login_bot()

    @patch.dict('os.environ', {'METABASE_USERNAME': 'testuser', 'METABASE_PASSWORD': 'testpass'}, clear=True)
    @patch('translate.services.requests.Session')
    def test_login_bot_login_failure(self, mock_session_class):
        # Simula login com resultado diferente de Success para cobrir raise correspondente
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_token = MagicMock()
        mock_get_token.json.return_value = {"query": {"tokens": {"logintoken": "tok"}}}
        mock_get_token.raise_for_status = Mock()

        mock_post_login = MagicMock()
        mock_post_login.json.return_value = {"login": {"result": "Fail"}}
        mock_post_login.raise_for_status = Mock()

        mock_session.get.side_effect = [mock_get_token]
        mock_session.post.return_value = mock_post_login

        client = MetabaseClient()
        with self.assertRaisesRegex(RuntimeError, r"Login failed for Metabase"):
            client.login_bot()

    @patch.dict('os.environ', {'METABASE_USERNAME': 'testuser', 'METABASE_PASSWORD': 'testpass'}, clear=True)
    @patch('translate.services.requests.Session')
    def test_login_bot_csrf_failure(self, mock_session_class):
        # Simula ausência de csrftoken após login bem-sucedido
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_token = MagicMock()
        mock_get_token.json.return_value = {"query": {"tokens": {"logintoken": "tok"}}}
        mock_get_token.raise_for_status = Mock()

        mock_post_login = MagicMock()
        mock_post_login.json.return_value = {"login": {"result": "Success"}}
        mock_post_login.raise_for_status = Mock()

        mock_get_csrf = MagicMock()
        mock_get_csrf.json.return_value = {"query": {"tokens": {}}}
        mock_get_csrf.raise_for_status = Mock()

        mock_session.get.side_effect = [mock_get_token, mock_get_csrf]
        mock_session.post.return_value = mock_post_login

        client = MetabaseClient()
        with self.assertRaisesRegex(RuntimeError, r"Failed to obtain CSRF token\."):
            client.login_bot()
    
    @patch.dict('os.environ', {}, clear=True)
    def test_login_bot_missing_credentials(self):
        client = MetabaseClient()
        with self.assertRaisesRegex(RuntimeError, r"Missing METABASE_USERNAME/METABASE_PASSWORD in settings_local\.py or env"):
            client.login_bot()
    
    @patch.dict('os.environ', {
        'METABASE_OAUTH_CONSUMER_KEY': 'key',
        'METABASE_OAUTH_CONSUMER_SECRET': 'secret'
    }, clear=True)
    @patch('translate.services.OAuth1Session')
    def test_login_user_oauth_success(self, mock_oauth_class):
        mock_session = MagicMock()
        mock_oauth_class.return_value = mock_session
        mock_session.get.return_value.json.return_value = {
            "query": {"tokens": {"csrftoken": "oauth_csrf"}}
        }
        mock_session.get.return_value.raise_for_status = Mock()
        
        client = MetabaseClient()
        result = client.login_user_oauth("access_token", "access_secret")
        
        assert result is client
        assert client._token == "oauth_csrf"

    def test_login_user_oauth_csrf_failure(self):
        mock_session = MagicMock()
        mock_session.get.return_value.json.return_value = {
            "query": {"tokens": {}}
        }
        mock_session.get.return_value.raise_for_status = Mock()
        
        with patch.dict('os.environ', {
            'METABASE_OAUTH_CONSUMER_KEY': 'key',
            'METABASE_OAUTH_CONSUMER_SECRET': 'secret'
        }, clear=True):
            with patch('translate.services.OAuth1Session', return_value=mock_session):
                client = MetabaseClient()
                with self.assertRaisesRegex(RuntimeError, r"Failed to obtain CSRF token via OAuth session\."):
                    client.login_user_oauth("access_token", "access_secret")

    @patch.dict('os.environ', {}, clear=True)
    def test_login_user_oauth_missing_consumer_keys(self):
        client = MetabaseClient()
        with self.assertRaisesRegex(RuntimeError, r"Missing METABASE_OAUTH_CONSUMER_KEY/SECRET"):
            client.login_user_oauth("access_token", "access_secret")
    
    @patch('translate.services.requests.get')
    def test_fetch_map_and_terms_success(self, mock_get):
        qids = ["Q1", "Q2"]
        
        map_response = {
            "results": {
                "bindings": [
                    {
                        "item": {"value": "https://metabase.wikibase.cloud/entity/Q100"},
                        "value": {"value": "Q1"}
                    }
                ]
            }
        }
        
        terms_response = {
            "results": {
                "bindings": [
                    {
                        "item": {"value": "https://metabase.wikibase.cloud/entity/Q101"},
                        "value": {"value": "Q2"},
                        "language": {"value": None},
                    },
                    {
                        "item": {"value": "https://metabase.wikibase.cloud/entity/Q100"},
                        "value": {"value": "Q1"},
                        "language": {"value": "en"},
                        "label": {"value": "Test Label"},
                        "description": {"value": "Test Description"}
                    }
                ]
            }
        }
        
        mock_get.side_effect = [
            Mock(json=Mock(return_value=map_response), raise_for_status=Mock()),
            Mock(json=Mock(return_value=terms_response), raise_for_status=Mock())
        ]
        
        client = MetabaseClient()
        result = client.fetch_map_and_terms(qids)
        
        assert "Q1" in result
        assert "en" in result["Q1"]
        assert result["Q1"]["en"]["label"] == "Test Label"
        assert result["Q1"]["en"]["metabase_id"] == "Q100"
        assert client.metabase_ids == {"Q1": "Q100"}
    
    def test_fetch_map_and_terms_empty_qids(self):
        client = MetabaseClient()
        result = client.fetch_map_and_terms([])
        assert result == {}
    
    def test_set_term_not_logged_in(self):
        client = MetabaseClient()
        with self.assertRaisesRegex(RuntimeError, r"not logged in"):
            client.set_term("Q1", "en", "label", "value", "user")
    
    def test_set_term_invalid_field(self):
        client = MetabaseClient()
        client._session = MagicMock()
        client._token = "token"
        with self.assertRaisesRegex(ValueError, r"field must be 'label' or 'description'"):
            client.set_term("Q1", "en", "invalid", "value", "user")
    
    def test_set_term_success(self):
        client = MetabaseClient()
        client._session = MagicMock()
        client._token = "token"
        client._session.post.return_value.json.return_value = {"success": True}
        client._session.post.return_value.raise_for_status = Mock()
        
        client.set_term("Q1", "en", "label", "New Label", "testuser")
        
        client._session.post.assert_called_once()
        call_args = client._session.post.call_args
        assert call_args[1]["data"]["action"] == "wbsetlabel"
        assert call_args[1]["data"]["value"] == "New Label"

    def test_set_term_api_error(self):
        client = MetabaseClient()
        client._session = MagicMock()
        client._token = "token"
        client._session.post.return_value.json.return_value = {"success": False, "error": "boom"}
        client._session.post.return_value.raise_for_status = Mock()

        with self.assertRaisesRegex(RuntimeError, r"boom"):
            client.set_term("Q1", "en", "label", "New Label", "testuser")
    
    def test_create_item_not_logged_in(self):
        client = MetabaseClient()
        with self.assertRaisesRegex(RuntimeError, r"not logged in"):
            client.create_item("Label")
    
    def test_create_item_success(self):
        client = MetabaseClient()
        client._session = MagicMock()
        client._token = "token"
        client._session.post.return_value.json.return_value = {
            "success": True,
            "entity": {"id": "Q999"}
        }
        client._session.post.return_value.raise_for_status = Mock()
        
        result = client.create_item("Test Skill", "A test skill", "en", "Q123", "admin")
        
        assert result == "Q999"
        client._session.post.assert_called_once()

    def test_save_item_error(self):
        client = MetabaseClient()
        client._session = MagicMock()
        client._token = "token"
        client._session.post.return_value.json.return_value = {"success": False, "error": "Error message"}
        client._session.post.return_value.raise_for_status = Mock()
        with self.assertRaisesRegex(RuntimeError, r"Error message"):
            client.create_item("Test Skill", "A test skill", "en", "Q123", "admin")

    def test_create_item_missing_entity_id(self):
        client = MetabaseClient()
        client._session = MagicMock()
        client._token = "token"
        client._session.post.return_value.json.return_value = {"success": True, "entity": {}}
        client._session.post.return_value.raise_for_status = Mock()

        with self.assertRaisesRegex(RuntimeError, r"did not return entity id"):
            client.create_item("Test Skill", "A test skill", "en", "Q123", "admin")
    
    def test_parse_entity_id_valid(self):
        client = MetabaseClient()
        uri = "https://metabase.wikibase.cloud/entity/Q42"
        assert client._parse_entity_id(uri) == "Q42"
    
    def test_parse_entity_id_invalid(self):
        client = MetabaseClient()
        assert client._parse_entity_id("https://example.com/entity/P1") is None
        assert client._parse_entity_id("invalid") is None

    def test_parse_entity_id_exception(self):
        client = MetabaseClient()
        assert client._parse_entity_id(None) is None


class TestBuildCapacityList(TestCase):
    
    def test_build_capacity_list_basic(self):
        terms_by_qid = {
            "Q1": {
                "en": {
                    "label": "English Label",
                    "description": "English Description",
                    "metabase_id": "Q100"
                },
                "es": {
                    "label": "Spanish Label",
                    "description": "Spanish Description",
                    "metabase_id": "Q100"
                }
            }
        }
        
        result = build_capacity_list(terms_by_qid, "es")
        
        assert len(result) == 1
        assert result[0]["qid"] == "Q1"
        assert result[0]["lang"] == "es"
        assert result[0]["label"] == "Spanish Label"
        assert result[0]["metabase_id"] == "Q100"
    
    def test_build_capacity_list_fallback_to_default(self):
        terms_by_qid = {
            "Q1": {
                "en": {
                    "label": "English Label",
                    "description": "English Description",
                    "metabase_id": "Q100"
                }
            }
        }
        
        result = build_capacity_list(terms_by_qid, "es", fallback="en")
        
        assert result[0]["lang"] == "es"
        assert result[0]["label"] is None
        assert result[0]["fallback_label"] == "English Label"
    
    def test_build_capacity_list_fallback_to_english(self):
        terms_by_qid = {
            "Q1": {
                "en": {
                    "label": "English Label",
                    "description": "English Description",
                    "metabase_id": "Q100"
                },
                "fr": {
                    "label": None,
                    "description": None,
                    "metabase_id": "Q100"
                }
            }
        }
        
        result = build_capacity_list(terms_by_qid, "de", fallback="fr")
        
        assert result[0]["fallback_label"] == "English Label"
        assert result[0]["fallback_description"] == "English Description"
    
    def test_build_capacity_list_multiple_items(self):
        terms_by_qid = {
            "Q1": {
                "en": {"label": "Item 1", "description": "Desc 1", "metabase_id": "Q100"}
            },
            "Q2": {
                "en": {"label": "Item 2", "description": "Desc 2", "metabase_id": "Q101"}
            }
        }
        
        result = build_capacity_list(terms_by_qid, "en")
        
        assert len(result) == 2
        assert result[0]["qid"] == "Q1"
        assert result[1]["qid"] == "Q2"