from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.management.commands.export import Command
from users.models import Profile, DataHash, Badge, UserBadge
from users.serializers import ProfileSerializer
from skills.models import Skill
from users.models import CustomUser
from io import StringIO
import hashlib, json
from django.core.management import call_command

class CommandTestCase(TestCase):
    def setUp(self):
        self.command = Command()
        self.command.verbosity = 2
        self.command.stdout = StringIO()
        testuser1 = CustomUser.objects.create(username='TestUser1')
        testuser2 = CustomUser.objects.create(username='TestUser2')
        Skill.objects.bulk_create([
            Skill(id=1, skill_wikidata_item='Q1'),
            Skill(id=2, skill_wikidata_item='Q2'),
            Skill(id=3, skill_wikidata_item='Q3'),
            Skill(id=4, skill_wikidata_item='Q4'),
            Skill(id=5, skill_wikidata_item='Q5'),
        ])

        profile1 = Profile.objects.get(user=testuser1)
        profile1.skills_known.set([1])
        profile1.skills_available.set([2])
        profile1.save()

        profile2 = Profile.objects.get(user=testuser2)
        profile2.skills_known.set([4])
        profile2.skills_available.set([5])
        profile2.wiki_alt = 'AltUser2'
        profile2.save()
        
        def_badge = Badge.objects.create(
            name='Badge1', 
            picture='https://common.wikimedia.org/wiki/File:Open_Badges_-_Logo.png', 
            description='Description1',
            logic='{"target": "account_age", "value": "0"}',
            type='internal'
        )
        self.user_badge1 = UserBadge.objects.create(
            user=testuser1,
            badge=def_badge,
            progress=100,
            is_displayed=True,
        )
        UserBadge.objects.create(
            user=testuser2,
            badge=def_badge,
            progress=100,
            is_displayed=True,
        )
        self.def_badge_id = def_badge.id

        self.profile_serializer = ProfileSerializer(Profile.objects.all(), many=True)

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

    def test_process_profiles(self):
        meta_wiki_users = ['TestUser1', 'AltUser2']
        formatted_data, skills, badges_meta = self.command.process_profiles(self.profile_serializer.data, meta_wiki_users)
        self.assertEqual(formatted_data, [
            ['TestUser1', '[1]', '[2]', f'[{self.def_badge_id}]'],
            ['AltUser2', '[4]', '[5]', f'[{self.def_badge_id}]']
        ])
        self.assertEqual(set(skills), {1, 2, 4, 5})
        self.assertEqual(badges_meta, [[self.def_badge_id, 'Badge1', 'Open Badges - Logo.png', '']])

    def test_process_profiles_no_meta_wiki_users(self):
        meta_wiki_users = []
        formatted_data, skills, badges_meta = self.command.process_profiles(self.profile_serializer.data, meta_wiki_users)
        self.assertEqual(formatted_data, [])
        self.assertEqual(skills, [])
        self.assertEqual(badges_meta, [])

    def test_process_profiles_partial_meta_wiki_users(self):
        meta_wiki_users = ['TestUser1']
        formatted_data, skills, badges_meta = self.command.process_profiles(self.profile_serializer.data, meta_wiki_users)
        self.assertEqual(formatted_data, [['TestUser1', '[1]', '[2]', f'[{self.def_badge_id}]']])
        self.assertEqual(set(skills), {1, 2})
        self.assertEqual(badges_meta, [[self.def_badge_id, 'Badge1', 'Open Badges - Logo.png', '']])

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
                    {"name": "badges", "type": "string"}
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
        self.assertIn('Login failed', str(context.exception))

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

    def test_hash_data(self):
        data = {"data": [['TestUser1', '[1]', '[2]', '[3]']]}
        expected_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()
        result = self.command.hash_data(data)
        self.assertEqual(result, expected_hash)

    @patch('users.management.commands.export.DataHash.objects.update_or_create')
    def test_save_current_hash(self, mock_update_or_create):
        data_type = 'users'
        hash_value = 'test_hash_value'
        mock_update_or_create.return_value = (MagicMock(), True)
        self.command.save_current_hash(data_type, hash_value)
        mock_update_or_create.assert_called_once_with(
            data_type=data_type,
            defaults={'hash_value': hash_value}
        )

    @patch('users.management.commands.export.DataHash.objects.get')
    def test_get_previous_hash_exists(self, mock_get):
        mock_get.return_value.hash_value = 'test_hash_value'
        result = self.command.get_previous_hash('users')
        self.assertEqual(result, 'test_hash_value')
        mock_get.assert_called_once_with(data_type='users')

    @patch('users.management.commands.export.DataHash.objects.get')
    def test_get_previous_hash_does_not_exist(self, mock_get):
        mock_get.side_effect = DataHash.DoesNotExist
        result = self.command.get_previous_hash('users')
        self.assertIsNone(result)
        mock_get.assert_called_once_with(data_type='users')

    def test_process_profiles_with_too_many_badges(self):
        # Create many internal badges for TestUser1 so the badges string exceeds 400 chars
        user = CustomUser.objects.get(username='TestUser1')
        for i in range(50):
            b = Badge.objects.create(
                name=f"BadgeName_{i}",
                picture='https://commons.wikimedia.org/wiki/File:Open_Badges_-_Logo.png',
                description='D',
                logic='{"source": "letsconnect"}',
                type='external'
            )
            UserBadge.objects.create(
                user=user,
                badge=b,
                progress=100,
                is_displayed=True,
                external_assertion_url='https://example.com/assertion/12345678901234567890'+str(i),
                external_issued_on='2024-01-01T00:00:00Z'
            )

        meta_wiki_users = ['TestUser1']
        formatted_data, _, _ = self.command.process_profiles(self.profile_serializer.data, meta_wiki_users)
        # Badges column is at index 3 and must be <= 400 chars after trimming
        self.assertTrue(len(formatted_data[0][3]) <= 400)

    def test_process_profiles_extract_hash_and_base(self):
        # Create many internal badges for TestUser1 so the badges string exceeds 400 chars
        user = CustomUser.objects.get(username='TestUser1')
        for i in range(3):
            Badge.objects.create(
                name=f"VeryLongBadgeName_{i}",
                picture='https://commons.wikimedia.org/wiki/File:Open_Badges_-_Logo.png',
                description='D',
                logic='{"source": "letsconnect"}',
                type='external'
            )
        badge0 = UserBadge.objects.create(
            user=user,
            badge=Badge.objects.get(name='VeryLongBadgeName_0'),
            progress=100,
            is_displayed=True,
            external_assertion_url='https://example.com/assertion/1234',
            external_issued_on='2024-01-01T00:00:00Z'
        )
        badge1 = UserBadge.objects.create(
            user=user,
            badge=Badge.objects.get(name='VeryLongBadgeName_1'),
            progress=100,
            is_displayed=True,
            external_assertion_url='example',
            external_issued_on='2024-01-01T00:00:00Z'
        )
        badge2 = UserBadge.objects.create(
            user=user,
            badge=Badge.objects.get(name='VeryLongBadgeName_2'),
            progress=100,
            is_displayed=True,
            external_assertion_url='',
            external_issued_on='2024-01-01T00:00:00Z'
        )

        meta_wiki_users = ['TestUser1']
        formatted_data, _, badges_meta = self.command.process_profiles(self.profile_serializer.data, meta_wiki_users)
        expected_formatted_data = [
            [
                'TestUser1',
                '[1]',
                '[2]',
                f'[{self.user_badge1.badge.id}, {badge0.badge.id}§1234, {badge1.badge.id}§example, {badge2.badge.id}]'
            ]
        ]
        expected_badges = [
            [1, 'Badge1', 'Open Badges - Logo.png', ''], 
            [2, 'VeryLongBadgeName_0', 'Open Badges - Logo.png', 'https://example.com/assertion/'], 
            [3, 'VeryLongBadgeName_1', 'Open Badges - Logo.png', ''], 
            [4, 'VeryLongBadgeName_2', 'Open Badges - Logo.png', '']
        ]
        self.assertEqual(formatted_data, expected_formatted_data)
        self.assertEqual(badges_meta, expected_badges)

    @patch('users.management.commands.export.requests.Session')
    def test_handle(self, mock_session):
        # Redirect stdout to suppress output during test
        with patch('users.management.commands.export.Profile.objects.all') as mock_profile_objects_all, \
             patch('users.management.commands.export.requests.get') as mock_requests_get, \
             patch('users.management.commands.export.Command.get_meta_wiki_users') as mock_get_meta_wiki_users, \
             patch('users.management.commands.export.Command.process_profiles') as mock_process_profiles, \
             patch('users.management.commands.export.Command.create_output_users') as mock_create_output_users, \
             patch('users.management.commands.export.Command.get_skill_dict') as mock_get_skill_dict, \
             patch('users.management.commands.export.Command.get_sparql_query') as mock_get_sparql_query, \
             patch('users.management.commands.export.Command.process_sparql_response') as mock_process_sparql_response, \
             patch('users.management.commands.export.Command.create_output_capacities') as mock_create_output_capacities, \
             patch('users.management.commands.export.Command.create_output_badges') as mock_create_output_badges, \
             patch('users.management.commands.export.Command.get_login_token') as mock_get_login_token, \
             patch('users.management.commands.export.Command.login') as mock_login, \
             patch('users.management.commands.export.Command.get_csrf_token') as mock_get_csrf_token, \
             patch('users.management.commands.export.Command.edit_page') as mock_edit_page:
            
            # Mocking the return values
            mock_profile_objects_all.return_value = []
            mock_get_meta_wiki_users.return_value = ['TestUser1']
            mock_process_profiles.return_value = ([], [], [])
            mock_create_output_users.return_value = {}
            mock_get_skill_dict.return_value = {}
            mock_get_sparql_query.return_value = 'sparql_query'
            mock_requests_get.return_value.json.return_value = {'results': {'bindings': []}}
            mock_process_sparql_response.return_value = []
            mock_create_output_capacities.return_value = {}
            mock_create_output_badges.return_value = {}
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
            mock_create_output_badges.assert_called_once()
            mock_get_login_token.assert_called_once()
            mock_login.assert_called_once()
            mock_get_csrf_token.assert_called()
            mock_edit_page.assert_called()

class AddArgumentsTestCase(TestCase):
    def test_add_arguments_dry_run(self):
        out = StringIO()
        call_command('export', '--dry-run', stdout=out)
        self.assertIn("Dry run mode enabled", out.getvalue())


