import secrets
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from ..models import Territory, Language, WikimediaProject, Organization, CustomUser, \
    Profile, LanguageProficiency


class TerritoryModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent_territory = Territory.objects.create(
            territory_name="Africa",
        )
        cls.territory = Territory.objects.create(
            territory_name="Nigeria",

        )
        cls.territory.parent_territory.set([cls.parent_territory])
        # cls.territory.parent_territory.set(1])

    def test_territory_creation(self):
        self.assertEqual(self.territory.territory_name, "Nigeria")
        self.assertEqual(str(self.territory), "Nigeria")

        self.assertIn(self.parent_territory, self.territory.parent_territory.all())

    def test_unique_territory_name(self):
        Territory.objects.create(territory_name="Asia")
        with self.assertRaises(IntegrityError):
            Territory.objects.create(territory_name="Asia")


class LanguageModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.language = Language.objects.create(
            language_name="Spanish",
            language_code="es"
        )

    def test_language_model_creation(self):
        self.assertEqual(self.language.language_name, "Spanish")
        self.assertEqual(self.language.language_code, "es")
        self.assertEqual(str(self.language), "Spanish")

    def test_unique_language_code(self):
        # Test that language_code is unique
        Language.objects.create(language_name="English", language_code="en")
        with self.assertRaises(IntegrityError):
            Language.objects.create(language_name="Hausa", language_code="en")


class WikimediaProjectModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wikimedia_project = WikimediaProject.objects.create(
            wikimedia_project_name="Wikipedia",
            wikimedia_project_code="wiki"
        )

    def test_wikimedia_project_creation(self):
        self.assertEqual(self.wikimedia_project.wikimedia_project_name, "Wikipedia")
        self.assertEqual(self.wikimedia_project.wikimedia_project_code, "wiki")
        self.assertEqual(str(self.wikimedia_project), "Wikipedia")

    def test_unique_wikimedia_project_code(self):
        WikimediaProject.objects.create(wikimedia_project_name="Wikimedia Commons", wikimedia_project_code="commonswiki")
        with self.assertRaises(IntegrityError):
            WikimediaProject.objects.create(wikimedia_project_name="Wikidata", wikimedia_project_code="commonswiki")


class CustomUserModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects._create_user(
            username="Abrahmovic",
            email="abrahmovic@hot.com",
            password=str(secrets.randbits(16)),
        )

    def test_custom_user_creation(self):
        self.assertEqual(self.user.username, "Abrahmovic")
        self.assertEqual(self.user.email, "abrahmovic@hot.com")

    def test_username_uniqueness(self):
        # Test the uniqueness of the username
        with self.assertRaises(IntegrityError):
            CustomUser.objects.create_user(
                username="Abrahmovic",
                email="another@example.com",
                password=str(secrets.randbits(16)),
            )


class ProfileModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.territory = Territory.objects.create(
            territory_name="Canada",
        )
        cls.language = Language.objects.create(
            language_name="French",
            language_code="fr"
        )

        cls.wikimedia_project = WikimediaProject.objects.create(
            wikimedia_project_name="Wikipedia",
            wikimedia_project_code="wiki"
        )
        cls.user = CustomUser.objects._create_user(
            username="Abrahmovic",
            email="abrahmovic@hot.com",
            password=str(secrets.randbits(16)),
        )

    def test_profile_creation(self):
        self.assertIsNotNone(self.user.profile)
        self.assertEqual(self.user.profile.user, self.user)

    def test_profile_fields(self):
        # Test filling in various fields of Profile
        profile = self.user.profile
        profile.pronoun = 'he-him'
        profile.contact_method = "wiki"
        profile.display_name = 'AbrahmotheBaller'
        profile.save()

        updated_profile = Profile.objects.get(id=profile.id)
        self.assertEqual(updated_profile.pronoun, 'he-him')
        self.assertEqual(updated_profile.display_name, 'AbrahmotheBaller')

    def test_invalid_pronoun_validation(self):
        profile = self.user.profile
        profile.pronoun = 'invalid_pronoun'
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_localization(self):
        profile = self.user.profile
        profile.territory.set([self.territory])
        profile.language.set([self.language])
        profile.wikimedia_project.set([self.wikimedia_project])
        profile.save()

        updated_profile = Profile.objects.get(id=profile.id)
        territory = [territory.territory_name for territory in updated_profile.territory.all()]
        language = [language.language_name for language in updated_profile.language.all()]
        wikimedia_project = [wikimedia_project.wikimedia_project_name for wikimedia_project in
                             updated_profile.wikimedia_project.all()]

        self.assertIn('Canada', territory)
        self.assertIn("French", language)
        self.assertIn("Wikipedia", wikimedia_project)

    def test_profile_str_method_with_only_username(self):
        user = CustomUser.objects.create_user(
            username="Anthony",
        )
        self.assertEqual(str(user.profile), "Anthony")

    def test_language_proficiency(self):
        profile = self.user.profile
        language = Language.objects.create(language_name="Spanish", language_code="es")
        LanguageProficiency.objects.create(profile=profile, language=language, proficiency='3')

        lang_prof = LanguageProficiency.objects.get(profile=profile, language=language)
        self.assertEqual(lang_prof.proficiency, '3')
        self.assertEqual(str(lang_prof), f"{profile.user.username} - {language.language_name} - {lang_prof.get_proficiency_display()}")

    def test_unique_language_proficiency(self):
        profile = self.user.profile
        language = Language.objects.create(language_name="Spanish", language_code="es")
        LanguageProficiency.objects.create(profile=profile, language=language, proficiency='3')

        with self.assertRaises(IntegrityError):
            LanguageProficiency.objects.create(profile=profile, language=language, proficiency='4')
