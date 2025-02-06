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
        


        # Process users
        formatted_data = []
        for profile in profile_serializer.data:
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

        output = {
            "license": "CC0-1.0",
            "description": {"en": "Users enrolled in the CapX platform",},
            "sources": "https://capx.toolforge.org",
            "schema": {
                "fields": [
                    {"name": "username", "title": "Username", "type": "string",},
                    {"name": "language", "title": "Languages", "type": "string",},
                    {"name": "skills_known", "title": "Skills Known", "type": "string",},
                    {"name": "skills_available", "title": "Skills Available", "type": "string",},
                    {"name": "skills_wanted", "title": "Skills Wanted", "type": "string",}
                ],
            },
            "data": formatted_data,
        }
        print(json.dumps(output, indent=4))

        # Get all skills that are known, available, and wanted
        skills = []
        for profile in profile_serializer.data:
            skills.extend(profile['skills_known'])
            skills.extend(profile['skills_available'])
            skills.extend(profile['skills_wanted'])

        # Remove duplicate skills
        skills = list(set(skills))

        # Get Wikidata items for each skill
        quids = [Skill.objects.get(id=skill).skill_wikidata_item for skill in skills]

        # Metabase SPARQL query
        query = """
        PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
        SELECT ?item ?itemLabel ?itemDescription ?value WHERE {
            VALUES ?value {
                %s
            }
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
        print(json.dumps(response.json(), indent=4))