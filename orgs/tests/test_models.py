from django.test import TestCase
from ..models import Organization, OrganizationType, TagDiff, Document, Management, OrganizationName
from users.models import CustomUser
import secrets


class OrganizationTypeModelTest(TestCase):

    def test_organization_type_creation(self):
        organization_type = OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )
        expected_type_code = f'{organization_type.type_code}'
        expected_type_name = f'{organization_type.type_name}'

        self.assertEqual(expected_type_code, 'org')
        self.assertEqual(expected_type_name, 'Organization')


class OrganizationModelTest(TestCase):
    def setUp(self):
        self.organization_type = OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )
        self.organization = Organization.objects.create(
            acronym='SO',
            type=self.organization_type,
        )
        OrganizationName.objects.create(
            organization=self.organization,
            name='Sample Organization',
            language_code='en'
        )
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))

    def test_organization_creation(self):
        organization = self.organization
        expected_acronym = f'{organization.acronym}'
        expected_type = f'{organization.type}'

        self.assertEqual(expected_acronym, 'SO')
        self.assertEqual(expected_type, 'Organization')
        # Ensure the English translation exists
        self.assertTrue(organization.i18n_names.filter(language_code='en', name='Sample Organization').exists())

    def test_organization_str_method_with_acronym(self):
        organization = self.organization
        # __str__ now uses the English name only
        self.assertEqual(str(organization), "Sample Organization")

    def test_organization_str_method_without_acronym(self):
        organization = Organization.objects.create()
        OrganizationName.objects.create(
            organization=organization,
            name='Organization 2',
            language_code='en'
        )
        self.assertEqual(str(organization), "Organization 2")

    def test_tagdiff(self):
        tagdiff = TagDiff.objects.create(tag="Test")
        self.assertEqual(str(tagdiff), "Test")

    def test_documents(self):
        url = Document.objects.create(url="https://commons.wikimedia.org/wiki/File:filename.ext")
        self.assertEqual(str(url), "File:filename.ext")

    def test_management_creation(self):
        management = Management.objects.create(
            organization=self.organization,
            user=self.user
        )
        self.assertEqual(management.organization, self.organization)
        self.assertEqual(management.user, self.user)
        # __str__ uses the organization's __str__ (English name only)
        self.assertEqual(str(management), f"{self.user.username} manages {self.organization}")

class OrganizationNameModelTest(TestCase):
    def setUp(self):
        self.organization_type = OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )
        self.organization = Organization.objects.create(
            acronym='SO',
            type=self.organization_type,
        )

    def test_organization_name_creation(self):
        org_name = OrganizationName.objects.create(
            organization=self.organization,
            name='Sample Organization',
            language_code='en'
        )
        expected_name = f'{org_name.name}'
        expected_language_code = f'{org_name.language_code}'

        self.assertEqual(expected_name, 'Sample Organization')
        self.assertEqual(expected_language_code, 'en')
        self.assertEqual(str(org_name), f"{self.organization.pk}:en=Sample Organization")