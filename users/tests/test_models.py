import secrets
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from orgs.models import Organization, OrganizationType
from ..models import Territory, Language, WikimediaProject, CustomUser, \
    Profile, LanguageProficiency, Avatar, create_user_profile, DataHash, \
    SavedItem, Badge, UserBadge


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


class AvatarModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.avatar = Avatar.objects.create(
            avatar_url='https://example.com/avatar.png'
        )

    def test_avatar_creation(self):
        self.assertEqual(self.avatar.avatar_url, 'https://example.com/avatar.png')
        self.assertEqual(str(self.avatar), 'https://example.com/avatar.png')


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

    def test_pk_mismatch(self):
        # Temporarily disconnect the signal
        post_save.disconnect(create_user_profile, sender=CustomUser)
        
        CustomUser.objects.create_user(
            username="Anthony",
            email="",
            password=str(secrets.randbits(16)),
        )
        user = CustomUser.objects.get(username="Anthony")
        self.assertFalse(hasattr(user, 'profile'))
        
        # Reconnect the signal
        post_save.connect(create_user_profile, sender=CustomUser)

        CustomUser.objects.create_user(
            username="Anthonie",
            email="",
            password=str(secrets.randbits(16)),
        )
        user = CustomUser.objects.get(username="Anthonie")
        self.assertTrue(hasattr(user, 'profile'))
        
        # Assert that both profile and user have the same pk
        self.assertEqual(user.pk, user.profile.pk)


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
        profile.languageproficiency_set.create(language=self.language, proficiency='3')
        profile.wikimedia_project.set([self.wikimedia_project])
        profile.save()

        updated_profile = Profile.objects.get(id=profile.id)
        territory = [territory.territory_name for territory in updated_profile.territory.all()]
        language = [language.language.language_name for language in updated_profile.languageproficiency_set.all()]
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
        self.assertEqual(str(lang_prof), f"{profile.user.username} - {language.language_name}")

    def test_unique_language_proficiency(self):
        profile = self.user.profile
        language = Language.objects.create(language_name="Spanish", language_code="es")
        LanguageProficiency.objects.create(profile=profile, language=language, proficiency='3')

        with self.assertRaises(IntegrityError):
            LanguageProficiency.objects.create(profile=profile, language=language, proficiency='4')

    def test_datahash_str_method(self):
        data_hash = DataHash.objects.create(
            data_type="test",
            hash_value="1234567890",
        )
        self.assertEqual(str(data_hash), "test: 1234567890")


class SavedItemModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects._create_user(
            username="TestUser",
            email="testuser@example.com",
            password=str(secrets.randbits(16)),
        )
        cls.other_user = CustomUser.objects._create_user(
            username="OtherUser",
            email="test2@example.com",
            password=str(secrets.randbits(16)),
        )
        cls.saved_item = SavedItem.objects.create(
            user=cls.user,
            relation="learner",
            entity="user",
            related_user=cls.other_user,
        )

    def test_saved_item_creation(self):
        self.assertEqual(self.saved_item.user, self.user)
        self.assertEqual(self.saved_item.relation, "learner")
        self.assertEqual(self.saved_item.entity, "user")
        self.assertEqual(self.saved_item.related_user, self.other_user)
        self.assertEqual(self.saved_item.related_org, None)
        self.assertIsNotNone(self.saved_item.created_at)

    def test_saved_item_str_method(self):
        self.assertEqual(
            str(self.saved_item),
            f"{self.user.username}: learner - User - OtherUser"
        )

        org_type = OrganizationType.objects.create(type_name="TestType")
        org = Organization.objects.create(display_name='Test Org', acronym='TO', type=org_type)
        saved_item = SavedItem.objects.create(
            user=self.user,
            relation="sharer",
            entity="org",
            related_org=org,
        )
        self.assertEqual(
            str(saved_item),
            f"{self.user.username}: sharer - Organization - Test Org"
        )

    def test_unique_saved_item(self):
        with self.assertRaises(ValidationError):
            SavedItem.objects.create(
                user=self.user,
                relation="learner",
                entity="user",
                related_user=self.other_user,
            )

        org_type = OrganizationType.objects.create(type_name="TestType")
        org = Organization.objects.create(display_name='Test Org', acronym='TO', type=org_type)
        SavedItem.objects.create(
            user=self.user,
            relation="sharer",
            entity="org",
            related_org=org,
        )

        with self.assertRaises(ValidationError):
            SavedItem.objects.create(
                user=self.user,
                relation="sharer",
                entity="org",
                related_org=org,
            )


    def test_different_saved_items(self):
        SavedItem.objects.create(
            user=self.user,
            relation="sharer",
            entity="user",
            related_user=self.other_user,
        )
        saved_items = SavedItem.objects.filter(user=self.user)
        self.assertEqual(saved_items.count(), 2)

    def test_both_related_org_and_related_user(self):
        org_type = OrganizationType.objects.create(type_name="TestType")
        org = Organization.objects.create(display_name='Test Org', acronym='TO', type=org_type)
        with self.assertRaises(ValidationError):
            SavedItem.objects.create(
                user=self.user,
                relation="sharer",
                entity="user",
                related_user=self.other_user,
                related_org=org,
            )

        with self.assertRaises(ValidationError):
            SavedItem.objects.create(
                user=self.user,
                relation="sharer",
                entity="org",
                related_user=self.other_user,
                related_org=org,
            )

    def test_invalid_entity_type(self):
        with self.assertRaises(ValidationError):
            SavedItem.objects.create(
                user=self.user,
                relation="sharer",
                entity="invalid",
                related_user=self.other_user,
            )

class BadgeModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.badge = Badge.objects.create(
            name="Test Badge",
            description="This is a test badge.",
        )

    def test_badge_creation(self):
        self.assertEqual(self.badge.name, "Test Badge")
        self.assertEqual(self.badge.description, "This is a test badge.")

    def test_badge_str_method(self):
        self.assertEqual(str(self.badge), "Test Badge")

class UserBadgeModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects._create_user(
            username="TestUser",
            email="testuser@example.com",
            password="password"
        )
        cls.badge = Badge.objects.create(
            name="Test Badge",
            description="This is a test badge.",
        )
        cls.user_badge = UserBadge.objects.create(
            profile=cls.user.profile,
            badge=cls.badge
        )

    def test_user_badge_creation(self):
        self.assertEqual(self.user_badge.profile, self.user.profile)
        self.assertEqual(self.user_badge.badge, self.badge)

    def test_user_badge_str_method(self):
        self.assertEqual(
            str(self.user_badge),
            f"{self.user.username} - {self.badge.name}"
        )