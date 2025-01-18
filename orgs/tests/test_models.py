from django.test import TestCase
from ..models import Organization, OrganizationType, TagDiff, Document


class OrganizationTypeModelTest(TestCase):

    def test_organization_type_creation(self):
        OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )
        organization_type = OrganizationType.objects.get(id=1)
        expected_type_code = f'{organization_type.type_code}'
        expected_type_name = f'{organization_type.type_name}'

        self.assertEqual(expected_type_code, 'org')
        self.assertEqual(expected_type_name, 'Organization')


class OrganizationModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a OrganizationType instance
        OrganizationType.objects.create(
            type_code='org',
            type_name='Organization'
        )

        # Create a Organization instance to use in tests
        Organization.objects.create(
            display_name='Sample Organization',
            acronym='SO',
            type=OrganizationType.objects.get(id=1),
        )

    def test_organization_creation(self):
        organization = Organization.objects.get(id=1)
        expected_display_name = f'{organization.display_name}'
        expected_acronym = f'{organization.acronym}'
        expected_type = f'{organization.type}'

        self.assertEqual(expected_display_name, 'Sample Organization')
        self.assertEqual(expected_acronym, 'SO')
        self.assertEqual(expected_type, 'Organization')

    def test_organization_str_method_with_acronym(self):
        organization = Organization.objects.get(id=1)
        self.assertEqual(str(organization), "Sample Organization (SO)")

    def test_organization_str_method_without_acronym(self):
        organization = Organization.objects.create(
            display_name="Organization 2"
        )
        self.assertEqual(str(organization), "Organization 2")

    def test_tagdiff(self):
        tagdiff = TagDiff.objects.create(tag="Test")
        self.assertEqual(str(tagdiff), "Test")

    def test_documents(self):
        url = Document.objects.create(url="https://commons.wikimedia.org/wiki/File:filename.ext")
        self.assertEqual(str(url), "File:filename.ext")