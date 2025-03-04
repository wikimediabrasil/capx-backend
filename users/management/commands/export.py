from django.core.management.base import BaseCommand
from users.serializers import ProfileSerializer
from users.models import Profile
from skills.models import Skill
from django.conf import settings
import json
import requests
import os

class Command(BaseCommand):
    help = "Export data to Commons in JSON tabular format"

    def format_list(self, data_list):
        return '[' + ', '.join(str(item) for item in data_list) + ']'

    def get_meta_wiki_users(self):
        query_params = {
            'action': 'query',
            'prop': 'transcludedin',
            'pageids': '12993801',  # Template:CapacityExchange
            'tilimit': 'max',
            'tiprop': 'title',
            'tinamespace': '2',
            'format': 'json',
            'formatversion': '2',
        }
        response = requests.get('https://meta.wikimedia.org/w/api.php', params=query_params)
        return [page['title'][5:] for page in response.json()['query']['pages'][0]['transcludedin']]

    def process_profiles(self, profiles, meta_wiki_users):
        formatted_data = []
        skills = []
        for profile in profiles:
            if profile['user']['username'] not in meta_wiki_users:
                continue

            data = [
                profile['user']['username'],
                self.format_list(profile['skills_known']),
                self.format_list(profile['skills_available']),
                self.format_list(profile['skills_wanted'])
            ]
            formatted_data.append(data)

            skills.extend(profile['skills_known'])
            skills.extend(profile['skills_available'])
            skills.extend(profile['skills_wanted'])

        return formatted_data, list(set(skills))

    def get_skill_dict(self, skills):
        return {Skill.objects.get(id=skill).skill_wikidata_item: skill for skill in skills}

    def get_sparql_query(self, quids):
        query = """
        PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
        SELECT ?item ?itemLabel ?itemDescription ?value WHERE {
            VALUES ?value { %s }
            ?item wbt:P1 ?value.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        """
        return query % ' '.join([f'"{quid}"' for quid in quids])

    def process_sparql_response(self, response, skill_dict):
        formatted_data = []
        for item in response.json()['results']['bindings']:
            data = [
                skill_dict[item['value']['value']],
                item['itemLabel']['value'] if 'itemLabel' in item else '',
                item['itemDescription']['value'] if 'itemDescription' in item else ''
            ]
            formatted_data.append(data)
        return formatted_data

    def create_output_users(self, formatted_data):
        return {
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

    def create_output_capacities(self, formatted_data):
        return {
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

    def get_login_token(self, session, url):
        params = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json"
        }
        response = session.get(url=url, params=params)
        data = response.json()
        return data['query']['tokens']['logintoken']

    def login(self, session, url, login_token):
        params = {
            "action": "login",
            "lgname": settings.CAPX_BOT_USERNAME,
            "lgpassword": settings.CAPX_BOT_PASSWORD,
            "lgtoken": login_token,
            "format": "json"
        }
        response = session.post(url, data=params).json()
        if response['login']['result'] != 'Success':
            raise requests.exceptions.RequestException("Login failed")

        return response

    def get_csrf_token(self, session, url):
        params = {
            "action": "query",
            "meta": "tokens",
            "format": "json"
        }
        response = session.get(url=url, params=params)
        data = response.json()
        return data['query']['tokens']['csrftoken']

    def edit_page(self, session, url, title, summary, text, csrf_token):
        params = {
            "action": "edit",
            "title": title,
            "summary": summary,
            "text": text,
            "token": csrf_token,
            "minor": "1",
            "format": "json"
        }
        response = session.post(url, data=params)
        return response.json()
        
    def handle(self, *args, **options):
        profile_serializer = ProfileSerializer(Profile.objects.all(), many=True)
        meta_wiki_users = self.get_meta_wiki_users()
        formatted_data, skills = self.process_profiles(profile_serializer.data, meta_wiki_users)
        output_users = self.create_output_users(formatted_data)

        skill_dict = self.get_skill_dict(skills)
        quids = list(skill_dict.keys())
        sparql_query = self.get_sparql_query(quids)
        response = requests.get(
            'https://metabase.wikibase.cloud/query/sparql',
            params={'query': sparql_query, 'format': 'json'}
        )
        formatted_data = self.process_sparql_response(response, skill_dict)
        output_capacities = self.create_output_capacities(formatted_data)

        session = requests.Session()
        url = "https://commons.wikimedia.org/w/api.php"
        login_token = self.get_login_token(session, url)
        self.login(session, url, login_token)

        csrf_token = self.get_csrf_token(session, url)
        self.edit_page(
            session, url, "Data:CapacityExchange/users.tab", "Updating data",
            json.dumps(output_users, indent=4), csrf_token
        )

        csrf_token = self.get_csrf_token(session, url)
        self.edit_page(
            session, url, "Data:CapacityExchange/capacities.tab", "Updating data",
            json.dumps(output_capacities, indent=4), csrf_token
        )