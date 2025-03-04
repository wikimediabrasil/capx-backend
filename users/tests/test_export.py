from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.management.commands.export import Command
from users.models import Profile
from skills.models import Skill

class CommandTestCase(TestCase):
    def setUp(self):
        self.command = Command()

    @patch('users.management.commands.export.requests.get')
    def test_get_meta_wiki_users(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'query': {
                'pages': [{
                    'transcludedin': [{'title': 'User:TestUser1'}, {'title': 'User:TestUser2'}]
                }]
            }
        }
        mock_get.return_value = mock_response

        result = self.command.get_meta_wiki_users()
        self.assertEqual(result, ['TestUser1', 'TestUser2'])

    def test_format_list(self):
        data_list = ['skill1', 'skill2', 'skill3']
        result = self.command.format_list(data_list)
        self.assertEqual(result, '[skill1, skill2, skill3]')

    @patch('users.management.commands.export.Profile.objects.all')
    def test_process_profiles(self, mock_profiles):
        mock_profiles.return_value = [
            {'user': {'username': 'TestUser1'}, 'skills_known': [1], 'skills_available': [2], 'skills_wanted': [3]},
            {'user': {'username': 'TestUser2'}, 'skills_known': [4], 'skills_available': [5], 'skills_wanted': [6]}
        ]
        meta_wiki_users = ['TestUser1']
        formatted_data, skills = self.command.process_profiles(mock_profiles.return_value, meta_wiki_users)
        self.assertEqual(formatted_data, [['TestUser1', '[1]', '[2]', '[3]']])
        self.assertEqual(skills, [1, 2, 3])

    @patch('users.management.commands.export.Skill.objects.get')
    def test_get_skill_dict(self, mock_get):
        mock_get.side_effect = lambda id: MagicMock(skill_wikidata_item=f'Q{id}')
        skills = [1, 2, 3]
        result = self.command.get_skill_dict(skills)
        self.assertEqual(result, {'Q1': 1, 'Q2': 2, 'Q3': 3})

    def test_get_sparql_query(self):
        quids = ['Q1', 'Q2', 'Q3']
        result = self.command.get_sparql_query(quids)
        expected_query = """
        PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
        SELECT ?item ?itemLabel ?itemDescription ?value WHERE {
            VALUES ?value { "Q1" "Q2" "Q3" }
            ?item wbt:P1 ?value.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        """
        self.assertEqual(result.strip(), expected_query.strip())

    @patch('users.management.commands.export.requests.get')
    def test_process_sparql_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': {
                'bindings': [
                    {'value': {'value': 'Q1'}, 'itemLabel': {'value': 'Skill1'}, 'itemDescription': {'value': 'Description1'}},
                    {'value': {'value': 'Q2'}, 'itemLabel': {'value': 'Skill2'}, 'itemDescription': {'value': 'Description2'}}
                ]
            }
        }
        mock_get.return_value = mock_response
        skill_dict = {'Q1': 1, 'Q2': 2}
        result = self.command.process_sparql_response(mock_response, skill_dict)
        self.assertEqual(result, [[1, 'Skill1', 'Description1'], [2, 'Skill2', 'Description2']])

    def test_create_output_users(self):
        formatted_data = [['TestUser1', '[1]', '[2]', '[3]']]
        result = self.command.create_output_users(formatted_data)
        expected_output = {
            "license": "CC0-1.0",
            "description": {"en": "Users enrolled in the CapX platform"},
            "sources": "https://capx.toolforge.org",
            "schema": {
                "fields": [
                    {"name": "username", "type": "string"},
                    {"name": "skills_known", "type": "string"},
                    {"name": "skills_available", "type": "string"},
                    {"name": "skills_wanted", "type": "string"}
                ],
            },
            "data": formatted_data,
        }
        self.assertEqual(result, expected_output)

    def test_create_output_capacities(self):
        formatted_data = [[1, 'Skill1', 'Description1']]
        result = self.command.create_output_capacities(formatted_data)
        expected_output = {
            "license": "CC0-1.0",
            "description": {"en": "Capacities added in the CapX platform"},
            "sources": "https://capx.toolforge.org",
            "schema": {
                "fields": [
                    {"name": "id", "type": "number"},
                    {"name": "name", "type": "string"},
                    {"name": "description", "type": "string"}
                ],
            },
            "data": formatted_data,
        }
        self.assertEqual(result, expected_output)

    @patch('users.management.commands.export.requests.Session')
    def test_get_login_token(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {'query': {'tokens': {'logintoken': 'test_token'}}}
        mock_session_instance.get.return_value = mock_response

        result = self.command.get_login_token(mock_session_instance, 'test_url')
        self.assertEqual(result, 'test_token')

    @patch('users.management.commands.export.requests.Session')
    def test_login(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {'login': {'result': 'Success'}}
        mock_session_instance.post.return_value = mock_response

        result = self.command.login(mock_session_instance, 'test_url', 'test_token')
        self.assertEqual(result, {'login': {'result': 'Success'}})

    @patch('users.management.commands.export.requests.Session')
    def test_login_failed(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {'login': {'result': 'Failed'}}
        mock_session_instance.post.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.command.login(mock_session_instance, 'test_url', 'test_token')
        self.assertEqual(str(context.exception), 'Login failed')        

    @patch('users.management.commands.export.requests.Session')
    def test_get_csrf_token(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {'query': {'tokens': {'csrftoken': 'test_csrf_token'}}}
        mock_session_instance.get.return_value = mock_response

        result = self.command.get_csrf_token(mock_session_instance, 'test_url')
        self.assertEqual(result, 'test_csrf_token')

    @patch('users.management.commands.export.requests.Session')
    def test_edit_page(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {'edit': {'result': 'Success'}}
        mock_session_instance.post.return_value = mock_response

        result = self.command.edit_page(mock_session_instance, 'test_url', 'test_title', 'test_summary', 'test_text', 'test_csrf_token')
        self.assertEqual(result, {'edit': {'result': 'Success'}})

    @patch('users.management.commands.export.requests.Session')
    @patch('users.management.commands.export.Profile.objects.all')
    @patch('users.management.commands.export.requests.get')
    @patch('users.management.commands.export.Command.get_meta_wiki_users')
    @patch('users.management.commands.export.Command.process_profiles')
    @patch('users.management.commands.export.Command.create_output_users')
    @patch('users.management.commands.export.Command.get_skill_dict')
    @patch('users.management.commands.export.Command.get_sparql_query')
    @patch('users.management.commands.export.Command.process_sparql_response')
    @patch('users.management.commands.export.Command.create_output_capacities')
    @patch('users.management.commands.export.Command.get_login_token')
    @patch('users.management.commands.export.Command.login')
    @patch('users.management.commands.export.Command.get_csrf_token')
    @patch('users.management.commands.export.Command.edit_page')
    def test_handle(
        self, mock_edit_page, mock_get_csrf_token, mock_login, mock_get_login_token,
        mock_create_output_capacities, mock_process_sparql_response, mock_get_sparql_query,
        mock_get_skill_dict, mock_create_output_users, mock_process_profiles,
        mock_get_meta_wiki_users, mock_requests_get, mock_profile_objects_all, mock_session
    ):
        # Mocking the return values
        mock_profile_objects_all.return_value = []
        mock_get_meta_wiki_users.return_value = ['TestUser1']
        mock_process_profiles.return_value = ([], [])
        mock_create_output_users.return_value = {}
        mock_get_skill_dict.return_value = {}
        mock_get_sparql_query.return_value = 'sparql_query'
        mock_requests_get.return_value.json.return_value = {'results': {'bindings': []}}
        mock_process_sparql_response.return_value = []
        mock_create_output_capacities.return_value = {}
        mock_get_login_token.return_value = 'test_login_token'
        mock_login.return_value = {'login': {'result': 'Success'}}
        mock_get_csrf_token.return_value = 'test_csrf_token'
        mock_edit_page.return_value = {'edit': {'result': 'Success'}}

        # Execute the handle method
        self.command.handle()

        # Assertions to ensure each method was called
        mock_profile_objects_all.assert_called_once()
        mock_get_meta_wiki_users.assert_called_once()
        mock_process_profiles.assert_called_once()
        mock_create_output_users.assert_called_once()
        mock_get_skill_dict.assert_called_once()
        mock_get_sparql_query.assert_called_once()
        mock_requests_get.assert_called_once()
        mock_process_sparql_response.assert_called_once()
        mock_create_output_capacities.assert_called_once()
        mock_get_login_token.assert_called_once()
        mock_login.assert_called_once()
        mock_get_csrf_token.assert_called()
        mock_edit_page.assert_called()