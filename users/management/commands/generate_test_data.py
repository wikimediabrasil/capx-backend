"""
Management command to generate test data for aggregation endpoints.

Usage:
    python manage.py generate_test_data
    python manage.py generate_test_data --users 50
    python manage.py generate_test_data --clear  # Clear existing test data first
"""

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import CustomUser, Profile, Language, Territory, LanguageProficiency
from skills.models import Skill


class Command(BaseCommand):
    help = "Generate test data for testing aggregation endpoints (languages/capacities by territory)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=20,
            help='Number of test users to create (default: 20)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before generating new data'
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='testuser_',
            help='Prefix for test usernames (default: testuser_)'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        clear = options['clear']
        prefix = options['prefix']

        if clear:
            self.clear_test_data(prefix)

        with transaction.atomic():
            languages = self.ensure_languages()
            territories = self.ensure_territories()
            skills = self.ensure_skills()
            self.create_test_users(num_users, prefix, languages, territories, skills)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully generated test data: {num_users} users with languages, territories, and skills'
        ))

    def clear_test_data(self, prefix):
        """Clear existing test users and their related data."""
        test_users = CustomUser.objects.filter(username__startswith=prefix)
        count = test_users.count()
        test_users.delete()
        self.stdout.write(self.style.WARNING(f'Cleared {count} existing test users'))

    def ensure_languages(self):
        """Ensure required languages exist and return them."""
        language_data = [
            ('en', 'English', 'English'),
            ('es', 'Spanish', 'Espa\u00f1ol'),
            ('pt', 'Portuguese', 'Portugu\u00eas'),
            ('fr', 'French', 'Fran\u00e7ais'),
            ('de', 'German', 'Deutsch'),
            ('ja', 'Japanese', '\u65e5\u672c\u8a9e'),
            ('zh', 'Chinese', '\u4e2d\u6587'),
            ('ar', 'Arabic', '\u0627\u0644\u0639\u0631\u0628\u064a\u0629'),
            ('hi', 'Hindi', '\u0939\u093f\u0928\u094d\u0926\u0940'),
            ('ru', 'Russian', '\u0420\u0443\u0441\u0441\u043a\u0438\u0439'),
        ]

        languages = []
        for code, name, autonym in language_data:
            lang, created = Language.objects.get_or_create(
                language_code=code,
                defaults={'language_name': name, 'language_autonym': autonym}
            )
            languages.append(lang)
            if created:
                self.stdout.write(f'  Created language: {name}')

        return languages

    def ensure_territories(self):
        """Ensure required territories exist with hierarchy and return them."""
        # Root territories (regions)
        root_territories_data = [
            'Northern America',
            'Latin America',
            'Europe',
            'Middle East and Africa',
            'South Asia',
            'East, Southeast Asia and Pacific',
            'Central and Eastern Europe',
        ]

        # Child territories mapping: {parent_name: [children]}
        child_territories_data = {
            'Northern America': ['United States', 'Canada'],
            'Latin America': ['Brazil', 'Mexico', 'Argentina', 'Chile'],
            'Europe': ['Germany', 'France', 'United Kingdom', 'Spain', 'Italy'],
            'Middle East and Africa': ['South Africa', 'Nigeria', 'Egypt', 'Israel'],
            'South Asia': ['India', 'Pakistan', 'Bangladesh'],
            'East, Southeast Asia and Pacific': ['Japan', 'Australia', 'Indonesia', 'Philippines'],
            'Central and Eastern Europe': ['Poland', 'Ukraine', 'Czech Republic'],
        }

        territories = {'roots': [], 'children': []}

        # Create root territories
        for name in root_territories_data:
            territory, created = Territory.objects.get_or_create(territory_name=name)
            territories['roots'].append(territory)
            if created:
                self.stdout.write(f'  Created root territory: {name}')

        # Create child territories with parent relationships
        for parent_name, children in child_territories_data.items():
            parent = Territory.objects.get(territory_name=parent_name)
            for child_name in children:
                child, created = Territory.objects.get_or_create(territory_name=child_name)
                if created:
                    self.stdout.write(f'  Created child territory: {child_name}')
                # Set parent relationship
                if not child.parent_territory.filter(pk=parent.pk).exists():
                    child.parent_territory.add(parent)
                territories['children'].append(child)

        return territories

    def ensure_skills(self):
        """Ensure required skills exist with hierarchy and return them."""
        # Root skills (7 main categories)
        root_skills_data = [
            ('Q10', 'Organizational Structure'),
            ('Q36', 'Communication'),
            ('Q50', 'Learning and Evaluation'),
            ('Q56', 'Community Health Initiative'),
            ('Q65', 'Social Skills'),
            ('Q74', 'Strategic Management'),
            ('Q106', 'Technology'),
        ]

        # Child skills mapping: {parent_qid: [child_qids]}
        child_skills_data = {
            'Q10': ['Q11', 'Q12', 'Q13', 'Q14', 'Q15'],
            'Q36': ['Q37', 'Q38', 'Q39', 'Q40', 'Q41'],
            'Q50': ['Q51', 'Q52', 'Q53', 'Q54', 'Q55'],
            'Q56': ['Q57', 'Q58', 'Q59', 'Q60'],
            'Q65': ['Q66', 'Q67', 'Q68', 'Q69', 'Q70'],
            'Q74': ['Q75', 'Q76', 'Q77', 'Q78', 'Q79'],
            'Q106': ['Q107', 'Q108', 'Q109', 'Q110', 'Q111'],
        }

        skills = {'roots': [], 'children': []}

        # Create root skills
        for qid, name in root_skills_data:
            skill, created = Skill.objects.get_or_create(
                skill_wikidata_item=qid,
                defaults={'skill_type': None}
            )
            skills['roots'].append(skill)
            if created:
                self.stdout.write(f'  Created root skill: {qid} ({name})')

        # Create child skills
        for parent_qid, child_qids in child_skills_data.items():
            parent = Skill.objects.get(skill_wikidata_item=parent_qid)
            for child_qid in child_qids:
                skill, created = Skill.objects.get_or_create(
                    skill_wikidata_item=child_qid,
                    defaults={'skill_type': parent}
                )
                skills['children'].append(skill)
                if created:
                    self.stdout.write(f'  Created child skill: {child_qid} (parent: {parent_qid})')

        return skills

    def create_test_users(self, num_users, prefix, languages, territories, skills):
        """Create test users with profiles, languages, and skills."""
        all_territories = territories['roots'] + territories['children']
        all_skills = skills['roots'] + skills['children']
        proficiency_levels = ['1', '2', '3', '4', '5', 'n']

        for i in range(num_users):
            username = f'{prefix}{i + 1}'

            # Skip if user already exists
            if CustomUser.objects.filter(username=username).exists():
                self.stdout.write(f'  Skipping existing user: {username}')
                continue

            # Create user (Profile is auto-created via signal)
            user = CustomUser.objects.create_user(
                username=username,
                email=f'{username}@example.com',
                password='testpassword123'
            )

            profile = user.profile

            # Assign random territories (1-3)
            user_territories = random.sample(all_territories, k=random.randint(1, 3))
            profile.territory.set(user_territories)

            # Assign random language proficiencies (2-5 languages)
            user_languages = random.sample(languages, k=random.randint(2, min(5, len(languages))))
            for lang in user_languages:
                LanguageProficiency.objects.create(
                    profile=profile,
                    language=lang,
                    proficiency=random.choice(proficiency_levels)
                )

            # Assign random skills
            # skills_known: 3-8 skills
            known_skills = random.sample(all_skills, k=random.randint(3, min(8, len(all_skills))))
            profile.skills_known.set(known_skills)

            # skills_available: subset of known skills (1-4)
            available_skills = random.sample(known_skills, k=random.randint(1, min(4, len(known_skills))))
            profile.skills_available.set(available_skills)

            # skills_wanted: different skills not in known (2-5)
            other_skills = [s for s in all_skills if s not in known_skills]
            wanted_skills = random.sample(other_skills, k=random.randint(2, min(5, len(other_skills))))
            profile.skills_wanted.set(wanted_skills)

            # Set display name and about
            profile.display_name = f'Test User {i + 1}'
            profile.about = f'This is test user {i + 1} for aggregation testing.'
            profile.save()

            self.stdout.write(f'  Created user: {username} with {len(user_territories)} territories, '
                            f'{len(user_languages)} languages, {len(known_skills)} known skills')

        self.stdout.write(self.style.SUCCESS(f'\nCreated {num_users} test users'))
