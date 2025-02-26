from django.core.management.base import BaseCommand
from users.serializers import ProfileSerializer, LanguageSerializer
from users.models import Profile, Language, LanguageProficiency
from skills.models import Skill
import json
import requests

class Command(BaseCommand):
    help = "Export data to Commons in JSON tabular format"

    def format_list(self, data_list):
        return '[' + ', '.join(str(item) for item in data_list) + ']'

    def handle(self, *args, **options):
        profile_serializer = ProfileSerializer(Profile.objects.all(), many=True)
        
        # Filter users that uses the template on the meta wiki page
        query_params = {
            'action': 'query',
            'prop': 'transcludedin',
            'pageids': '12493945', # Template:CapXsupporter, for testing purposes
            'tilimit': 'max',
            'tiprop': 'title',
            'tinamespace': '2',
            'format': 'json',
            'formatversion': '2',
        }
        response = requests.get('https://meta.wikimedia.org/w/api.php', params=query_params)
        meta_wiki_users = [page['title'][5:] for page in response.json()['query']['pages'][0]['transcludedin']]

        # Process users
        formatted_data = []
        skills = []
        for profile in profile_serializer.data:
            if profile['user']['username'] not in meta_wiki_users:
                continue

            profile_id = Profile.objects.get(user_id=profile['user']['id']).id
            language_proficiencies = LanguageProficiency.objects.filter(profile_id=profile_id).select_related('language')

            data = [
                profile['user']['username'],
                self.format_list([f"{lp.language.language_code}-{lp.proficiency}" for lp in language_proficiencies]),
                self.format_list(profile['skills_known']),
                self.format_list(profile['skills_available']),
                self.format_list(profile['skills_wanted'])
            ]
            formatted_data.append(data)

            skills.extend(profile['skills_known'])
            skills.extend(profile['skills_available'])
            skills.extend(profile['skills_wanted'])

        output = {
            "license": "CC0-1.0",
            "description": {"en": "Users enrolled in the CapX platform",},
            "sources": "https://capx.toolforge.org",
            "schema": {
                "fields": [
                    {"name": "username", "type": "string",},
                    {"name": "language", "type": "string",},
                    {"name": "skills_known", "type": "string",},
                    {"name": "skills_available", "type": "string",},
                    {"name": "skills_wanted", "type": "string",}
                ],
            },
            "data": formatted_data,
        }
        print(json.dumps(output, indent=4))


        # Remove duplicate skills
        skills = list(set(skills))

        # Get Wikidata items for each skill
        skill_dict = {Skill.objects.get(id=skill).skill_wikidata_item: skill for skill in skills}

        # Create a list of QIDs
        quids = list(skill_dict.keys())

        # Metabase SPARQL query
        query = """
        PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
        SELECT ?item ?itemLabel ?itemDescription ?value WHERE {
            VALUES ?value { %s }
            ?item wbt:P1 ?value.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        """

        # Print the formatted query
        final = query % ' '.join([f'"{quid}"' for quid in quids])

        # Run the query in Metabase
        response = requests.get(
            'https://metabase.wikibase.cloud/query/sparql',
            params={'query': final, 'format': 'json'}
        )

        # Process capacities
        formatted_data = []
        for item in response.json()['results']['bindings']:
            data = [
                skill_dict[item['value']['value']],
                item['itemLabel']['value'] if 'itemLabel' in item else '',
                item['itemDescription']['value'] if 'itemDescription' in item else ''
            ]
            formatted_data.append(data)

        output = {
            "license": "CC0-1.0",
            "description": {"en": "Capacities added in the CapX platform",},
            "sources": "https://capx.toolforge.org",
            "schema": {
                "fields": [
                    {"name": "id", "type": "number",},
                    {"name": "name", "type": "string",},
                    {"name": "description", "type": "string",}
                ],
            },
            "data": formatted_data,
        }
        print(json.dumps(output, indent=4))
