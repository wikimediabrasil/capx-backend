from django.core.management.base import BaseCommand
from users.serializers import ProfileSerializer, LanguageSerializer
from users.models import Profile, Language, LanguageProficiency
import json

class Command(BaseCommand):
    help = "Export data to Commons in JSON tabular format"

    def format_list(self, data_list):
        return '[' + ', '.join(str(item) for item in data_list) + ']'

    def handle(self, *args, **options):
        profile_serializer = ProfileSerializer(Profile.objects.all(), many=True)
        


        # Process users
        formatted_data = []
        for profile in profile_serializer.data:
            print(profile)
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
