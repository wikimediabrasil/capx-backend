from django.core.management.base import BaseCommand
from users.serializers import ProfileSerializer
from users.models import Profile, DataHash
from skills.models import Skill
from django.conf import settings
from users.models import CustomUser, UserBadge
import json
import requests
import hashlib
import os

class Command(BaseCommand):
    help = "Export data to Commons in JSON tabular format"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Skip login/session steps and print JSON instead of saving pages'
        )

    def format_list(self, data_list):
        def escape_commas(item):
            return item.replace(',', '&#44;') if isinstance(item, str) else item
        return '[' + ', '.join(str(escape_commas(item)) for item in data_list) + ']'

    def get_user_agent(self):
        version = getattr(settings, "SPECTACULAR_SETTINGS", {}).get("VERSION", "dev")
        return f"CapacityExchangeBot/{version}"

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
        response = requests.get(
            'https://meta.wikimedia.org/w/api.php',
            params=query_params,
            headers={'User-Agent': self.get_user_agent()}
        )
        if self.verbosity >= 2:
            self.stdout.write(f"Meta wiki users response: {response.json()}")
        return [page['title'][5:] for page in response.json()['query']['pages'][0]['transcludedin']]

    def process_profiles(self, profiles, meta_wiki_users):
        formatted_data = []
        skills = []
        processed_usernames = set()
        export_rows = []

        # First pass - process regular usernames
        for profile in profiles:
            username = profile['user']['username']
            if username in meta_wiki_users:
                data = [
                    username,
                    self.format_list(profile['skills_known']),
                    self.format_list(profile['skills_available']),
                ]
                export_rows.append((data, username))  # (dados, username_principal)
                processed_usernames.add(username)

                skills.extend(profile['skills_known'])
                skills.extend(profile['skills_available'])
        
        # Second pass - process alternative usernames if not already processed
        for profile in profiles:
            if 'wiki_alt' in profile and profile['wiki_alt'] and profile['wiki_alt'] in meta_wiki_users:
                alt_username = profile['wiki_alt']
                if alt_username not in processed_usernames:
                    data = [
                        alt_username,
                        self.format_list(profile['skills_known']),
                        self.format_list(profile['skills_available']),
                    ]
                    export_rows.append((data, profile['user']['username']))  # (dados, username_principal)
                    processed_usernames.add(alt_username)

                    skills.extend(profile['skills_known'])
                    skills.extend(profile['skills_available'])

        # Get badges from UserBadges and Wikilearn
        for data, main_username in export_rows:
            badges = []
            user = CustomUser.objects.get(username=main_username)
            user_badges = UserBadge.objects.filter(user=user, progress=100, is_displayed=True)
            for badge in user_badges:
                image = badge.badge.picture.split('/')[-1]
                badge_data = f"{badge.badge.name}§{image}§"
                badges.append(badge_data)

            api = f"https://learn.wiki/api/badges/v1/assertions/user/{main_username}/"
            response = requests.get(api, headers={'User-Agent': self.get_user_agent()})
            if response.status_code == 200 and response.json().get('results', None):
                for badge in response.json().get('results'):
                    badge_data = f"{badge['badge_class']['display_name']}§Open Badges - Logo.png§{badge['assertion_url']}"
                    badges.append(badge_data)

            # Remove last badges if the formatted string exceeds 400 chars
            formatted_badges = self.format_list(badges)
            while len(formatted_badges) > 400 and badges:
                badges.pop()
                formatted_badges = self.format_list(badges)

            data.append(formatted_badges)
            formatted_data.append(data)
        
        if self.verbosity >= 2:
            self.stdout.write(f"Processed profiles: {formatted_data}")
            self.stdout.write(f"Skills: {skills}")

        return formatted_data, list(set(skills))

    def get_skill_dict(self, skills):
        skill_dict = {Skill.objects.get(id=skill).skill_wikidata_item: skill for skill in skills}
        if self.verbosity >= 2:
            self.stdout.write(f"Skill dictionary: {skill_dict}")
        return skill_dict

    def get_sparql_query(self, quids):
        query = """
        PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
        SELECT ?item ?itemLabel ?itemDescription ?value WHERE {
            VALUES ?value { %s }
            ?item wbt:P1 ?value.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        """
        sparql_query = query % ' '.join([f'"{quid}"' for quid in quids])
        if self.verbosity >= 2:
            self.stdout.write(f"SPARQL query: {sparql_query}")
        return sparql_query

    def process_sparql_response(self, response, skill_dict):
        formatted_data = []
        for item in response.json()['results']['bindings']:
            data = [
                skill_dict[item['value']['value']],
                item['itemLabel']['value'] if 'itemLabel' in item else '',
                item['itemDescription']['value'] if 'itemDescription' in item else ''
            ]
            formatted_data.append(data)
        if self.verbosity >= 2:
            self.stdout.write(f"SPARQL response data: {formatted_data}")
        return formatted_data

    def create_output_users(self, formatted_data):
        output_users = {
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
        if self.verbosity >= 2:
            self.stdout.write(f"Output users: {output_users}")
        return output_users

    def create_output_capacities(self, formatted_data):
        output_capacities = {
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
        if self.verbosity >= 2:
            self.stdout.write(f"Output capacities: {output_capacities}")
        return output_capacities

    def get_login_token(self, session, url):
        params = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json"
        }
        response = session.get(url=url, params=params, headers={'User-Agent': self.get_user_agent()})
        data = response.json()
        if self.verbosity >= 2:
            self.stdout.write(f"Login token response: {data}")
        return data['query']['tokens']['logintoken']

    def login(self, session, url, login_token):
        params = {
            "action": "login",
            "lgname": settings.CAPX_BOT_USERNAME,
            "lgpassword": settings.CAPX_BOT_PASSWORD,
            "lgtoken": login_token,
            "format": "json"
        }
        response = session.post(url, data=params, headers={'User-Agent': self.get_user_agent()}).json()
        if response['login']['result'] != 'Success':
            raise requests.exceptions.RequestException("Login failed")
        if self.verbosity >= 2:
            self.stdout.write(f"Login response: {response}")
        return response

    def get_csrf_token(self, session, url):
        params = {
            "action": "query",
            "meta": "tokens",
            "format": "json"
        }
        response = session.get(url=url, params=params, headers={'User-Agent': self.get_user_agent()})
        data = response.json()
        if self.verbosity >= 2:
            self.stdout.write(f"CSRF token response: {data}")
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
        if self.verbosity >= 2:
            self.stdout.write(f"Editing page {title} with text: {text}")
        
        response = session.post(url, data=params, headers={'User-Agent': self.get_user_agent()})
        return response.json()

    def hash_data(self, data):
        hash_value = hashlib.sha256(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()
        if self.verbosity >= 2:
            self.stdout.write(f"Hashed data: {hash_value}")
        return hash_value

    def get_previous_hash(self, data_type):
        try:
            hash_value = DataHash.objects.get(data_type=data_type).hash_value
            if self.verbosity >= 2:
                self.stdout.write(f"Previous hash for {data_type}: {hash_value}")
            return hash_value
        except DataHash.DoesNotExist:
            if self.verbosity >= 2:
                self.stdout.write(f"No previous hash found for {data_type}")
            return None

    def save_current_hash(self, data_type, hash_value):
        data_hash, _ = DataHash.objects.update_or_create(
            data_type=data_type,
            defaults={'hash_value': hash_value}
        )
        if self.verbosity >= 2:
            self.stdout.write(f"Saved current hash for {data_type}: {hash_value}")
        return data_hash
        
    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        dry_run = options.get('dry_run', False)  # Add a dry-run option

        profile_serializer = ProfileSerializer(Profile.objects.all(), many=True)
        meta_wiki_users = self.get_meta_wiki_users()
        formatted_data, skills = self.process_profiles(profile_serializer.data, meta_wiki_users)
        output_users = self.create_output_users(formatted_data)

        skill_dict = self.get_skill_dict(skills)
        quids = list(skill_dict.keys())
        sparql_query = self.get_sparql_query(quids)
        response = requests.get(
            'https://metabase.wikibase.cloud/query/sparql',
            params={'query': sparql_query, 'format': 'json'},
            headers={'User-Agent': self.get_user_agent()}
        )
        formatted_data = self.process_sparql_response(response, skill_dict)
        output_capacities = self.create_output_capacities(formatted_data)

        # Hash current data
        current_users_hash = self.hash_data(output_users)
        current_capacities_hash = self.hash_data(output_capacities)

        # Get previous hashes from the database
        previous_users_hash = self.get_previous_hash('users')
        previous_capacities_hash = self.get_previous_hash('capacities')

        # Check if data has changed
        if current_users_hash != previous_users_hash or current_capacities_hash != previous_capacities_hash:
            if dry_run:
                # Print JSON instead of saving
                self.stdout.write("Dry run mode enabled. Outputting JSON data:")
                self.stdout.write("Users JSON:")
                self.stdout.write(json.dumps(output_users, indent=4))
                self.stdout.write("Capacities JSON:")
                self.stdout.write(json.dumps(output_capacities, indent=4))
            else:
                session = requests.Session()
                url = "https://commons.wikimedia.org/w/api.php"
                login_token = self.get_login_token(session, url)
                self.login(session, url, login_token)

                if current_users_hash != previous_users_hash:
                    csrf_token = self.get_csrf_token(session, url)
                    self.edit_page(
                        session, url, "Data:CapacityExchange/users.tab", "Updating data",
                        json.dumps(output_users, indent=4), csrf_token
                    )
                    self.save_current_hash('users', current_users_hash)

                if current_capacities_hash != previous_capacities_hash:
                    csrf_token = self.get_csrf_token(session, url)
                    self.edit_page(
                        session, url, "Data:CapacityExchange/capacities.tab", "Updating data",
                        json.dumps(output_capacities, indent=4), csrf_token
                    )
                    self.save_current_hash('capacities', current_capacities_hash)
