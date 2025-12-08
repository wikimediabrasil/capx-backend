from django.core.management.base import BaseCommand
from users.serializers import ProfileSerializer
from users.models import Profile, DataHash
from skills.models import Skill
from users.models import CustomUser, UserBadge
from CapX.useragent import get_user_agent
from django.conf import settings
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
            headers={'User-Agent': get_user_agent('Export')}
        )
        if self.verbosity >= 2:
            self.stdout.write(f"Meta wiki users response: {response.json()}")
        return [page['title'][5:] for page in response.json()['query']['pages'][0]['transcludedin']]

    def process_profiles(self, profiles, meta_wiki_users):
        formatted_data = []
        skills = []
        processed_usernames = set()
        export_rows = []
        badge_meta_map = {}

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

        # Helper to extract assertion hash and base URL from a full assertion URL
        def extract_hash_and_base(url: str):
            clean = url.split('#', 1)[0].split('?', 1)[0]
            parts = [p for p in clean.split('/') if p]
            if len(parts) < 2:
                return url, ""
            hash_code = parts[-1]
            base_url = clean[: clean.rfind(hash_code)].rstrip('/') + '/'
            return hash_code, base_url

        # Get badges from UserBadges
        for data, main_username in export_rows:
            badges_for_user = []
            user = CustomUser.objects.get(username=main_username)
            user_badges = UserBadge.objects.filter(user=user, progress=100, is_displayed=True)
            for user_badge in user_badges:
                badge = user_badge.badge
                image = badge.picture.split('/')[-1].split('?', 1)[0] if badge.picture.startswith('https://commons.wikimedia.org/wiki/Special:Redirect/file/') else 'Open Badges - Logo.png'
                # Collect global metadata once per badge id
                if badge.id not in badge_meta_map:
                    badge_meta_map[badge.id] = {
                        'id': badge.id,
                        'name': badge.name,
                        'image': image,
                        'base_url': ''
                    }
                # For users.tab keep minimal info: internal -> id ; external -> id§hash
                if badge.type == 'external' and user_badge.external_assertion_url:
                    hash_code, base_url = extract_hash_and_base(user_badge.external_assertion_url)
                    if base_url and not badge_meta_map[badge.id].get('base_url'):
                        badge_meta_map[badge.id]['base_url'] = base_url
                    badges_for_user.append(f"{badge.id}§{hash_code}")
                else:
                    badges_for_user.append(str(badge.id))

            # Remove last badges if the formatted string exceeds 400 chars
            formatted_badges = self.format_list(badges_for_user)
            while len(formatted_badges) > 400 and badges_for_user:
                badges_for_user.pop()
                formatted_badges = self.format_list(badges_for_user)

            data.append(formatted_badges)
            formatted_data.append(data)
        
        if self.verbosity >= 2:
            self.stdout.write(f"Processed profiles: {formatted_data}")
            self.stdout.write(f"Skills: {skills}")

        # Prepare badge metadata list (stable ordering by id)
        badges_meta = [[meta['id'], meta['name'], meta['image'], meta.get('base_url', '')] for _, meta in sorted(badge_meta_map.items(), key=lambda kv: kv[0])]
        return formatted_data, list(set(skills)), badges_meta

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
                item['itemDescription']['value'] if 'itemDescription' in item else '',
                item['value']['value'] if 'value' in item else '',
            ]
            formatted_data.append(data)
        if self.verbosity >= 2:
            self.stdout.write(f"SPARQL response data: {formatted_data}")
        return formatted_data

    def fetch_localized_capacities(self, quids):
        """
        Fetch localized labels and descriptions from Metabase for given QIDs.
        Returns a mapping: { qid: { lang: { 'label': str|None, 'description': str|None } } }
        """
        quids = [q for q in quids if q]
        if not quids:
            return {}
        item_ids = " ".join(f"'{qid}'" for qid in quids)
        query = f"""PREFIX wbt:<https://metabase.wikibase.cloud/prop/direct/>
            PREFIX wb: <https://metabase.wikibase.cloud/entity/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX schema: <http://schema.org/>
            SELECT ?item ?value ?language (SAMPLE(?label) AS ?label) (SAMPLE(?description) AS ?description) WHERE {{  
                VALUES ?value {{ {item_ids} }}
                ?item wbt:P5 wb:Q34531.
                ?item wbt:P67/wbt:P1 ?value.  
                {{
                    ?item rdfs:label ?label.
                    BIND(LANG(?label) AS ?language)
                }}
                UNION
                {{
                    ?item schema:description ?description.
                    BIND(LANG(?description) AS ?language)
                }}
            }}
            GROUP BY ?item ?value ?language
            ORDER BY ?language
            """
        headers = {'User-Agent': get_user_agent('Export'), 'Accept': 'application/sparql-results+json'}
        response = requests.get(
            'https://metabase.wikibase.cloud/query/sparql',
            params={'query': query},
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if self.verbosity >= 2:
            self.stdout.write(f"Localized capacities SPARQL rows: {len(data.get('results', {}).get('bindings', []))}")
        localized: dict[str, dict[str, dict[str, str | None]]] = {}
        for b in data.get('results', {}).get('bindings', []):
            qid = b.get('value', {}).get('value')
            lang = b.get('language', {}).get('value')
            label = b.get('label', {}).get('value')
            description = b.get('description', {}).get('value')
            if not qid or not lang:
                continue
            entry = localized.setdefault(qid, {}).setdefault(lang, {'label': None, 'description': None})
            if label is not None:
                entry['label'] = label
            if description is not None:
                entry['description'] = description
        # Enforce max length per localized string (truncate to 397 + '...')
        MAX_LEN = 400
        ELLIPSIS = '...'
        TRUNC_LEN = MAX_LEN - len(ELLIPSIS)
        for qid, lang_map in localized.items():
            for lang, vals in lang_map.items():
                for field in ('label', 'description'):
                    v = vals.get(field)
                    if v and len(v) > MAX_LEN:
                        vals[field] = v[:TRUNC_LEN].rstrip() + ELLIPSIS
                        if self.verbosity >= 2:
                            self.stdout.write(f"Truncated {field} for {qid}/{lang} to {MAX_LEN} chars")
        if self.verbosity >= 2:
            self.stdout.write(f"Localized capacities map keys (qids): {list(localized.keys())}")
        return localized

    def build_localized_capacities_rows(self, quids, skill_dict, localized_terms):
        """
        Build rows: [id, {lang: label}, {lang: description}, qid]
        """
        rows = []
        # stable order by Skill id when possible
        for qid in sorted(skill_dict.keys(), key=lambda q: skill_dict[q]):
            sid = skill_dict[qid]
            langs = localized_terms.get(qid, {})
            name_obj = {lang: terms['label'] for lang, terms in langs.items() if terms.get('label')}
            desc_obj = {lang: terms['description'] for lang, terms in langs.items() if terms.get('description')}
            rows.append([sid, name_obj, desc_obj, qid])
        if self.verbosity >= 2:
            self.stdout.write(f"Localized capacities rows built: {len(rows)}")
        return rows

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
                    {"name": "name", "type": "localized"},
                    {"name": "description", "type": "localized"},
                    {"name": "wikidata_item", "type": "string"}
                ],
            },
            "data": formatted_data,
        }
        if self.verbosity >= 2:
            self.stdout.write(f"Output capacities: {output_capacities}")
        return output_capacities

    def create_output_badges(self, formatted_data):
        output_badges = {
            "license": "CC0-1.0",
            "description": {"en": "Badges available in the CapX platform"},
            "sources": "https://capx.toolforge.org",
            "schema": {
                "fields": [
                    {"name": "id", "type": "number"},
                    {"name": "name", "type": "string"},
                    {"name": "image", "type": "string"},
                    {"name": "base_url", "type": "string"}
                ],
            },
            "data": formatted_data,
        }
        if self.verbosity >= 2:
            self.stdout.write(f"Output badges: {output_badges}")
        return output_badges

    def get_login_token(self, session, url):
        params = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json"
        }
        response = session.get(url=url, params=params, headers={'User-Agent': get_user_agent('Export')})
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
        response = session.post(url, data=params, headers={'User-Agent': get_user_agent('Export')}).json()
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
        response = session.get(url=url, params=params, headers={'User-Agent': get_user_agent('Export')})
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
        
        response = session.post(url, data=params, headers={'User-Agent': get_user_agent('Export')})
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
        formatted_data, _skills, badges_meta = self.process_profiles(profile_serializer.data, meta_wiki_users)
        # Overwrite skills with all skills in the DB instead of only those in use on Meta profiles
        skills = list(Skill.objects.values_list('id', flat=True))
        output_users = self.create_output_users(formatted_data)

        skill_dict = self.get_skill_dict(skills)
        quids = list(skill_dict.keys())
        # Fetch all localized terms for capacities in one go and build localized rows
        localized_terms = self.fetch_localized_capacities(quids)
        capacities_rows = self.build_localized_capacities_rows(quids, skill_dict, localized_terms)
        output_capacities = self.create_output_capacities(capacities_rows)
        output_badges = self.create_output_badges(badges_meta)

        # Hash current data
        current_users_hash = self.hash_data(output_users)
        current_capacities_hash = self.hash_data(output_capacities)
        current_badges_hash = self.hash_data(output_badges)

        # Get previous hashes from the database
        previous_users_hash = self.get_previous_hash('users')
        previous_capacities_hash = self.get_previous_hash('capacities')
        previous_badges_hash = self.get_previous_hash('badges')

        # Check if data has changed
        if (current_users_hash != previous_users_hash or
            current_capacities_hash != previous_capacities_hash or
            current_badges_hash != previous_badges_hash):
            if dry_run:
                # Print JSON instead of saving
                self.stdout.write("Dry run mode enabled. Outputting JSON data:")
                self.stdout.write("Users JSON:")
                self.stdout.write(json.dumps(output_users, indent=4))
                self.stdout.write("Capacities JSON:")
                self.stdout.write(json.dumps(output_capacities, indent=4))
                self.stdout.write("Badges JSON:")
                self.stdout.write(json.dumps(output_badges, indent=4))
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

                if current_badges_hash != previous_badges_hash:
                    csrf_token = self.get_csrf_token(session, url)
                    self.edit_page(
                        session, url, "Data:CapacityExchange/badges.tab", "Updating data",
                        json.dumps(output_badges, indent=4), csrf_token
                    )
                    self.save_current_hash('badges', current_badges_hash)
