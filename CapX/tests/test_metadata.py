from django.test import TestCase
from rest_framework.serializers import CharField, ChoiceField
from rest_framework.metadata import SimpleMetadata
from CapX.metadata import CustomMetadata
from rest_framework.serializers import ManyRelatedField
from unittest.mock import MagicMock
from unittest.mock import PropertyMock


class CustomMetadataTestCase(TestCase):
    def setUp(self):
        self.metadata = CustomMetadata()
        self.many_related_field = ManyRelatedField(
            child_relation=MagicMock()
        )
        type(self.many_related_field).choices = PropertyMock(return_value={'1': 'One', '2': 'Two'})

    def test_get_field_info_with_many_related_field(self):
        field_info = self.metadata.get_field_info(self.many_related_field)
        expected_choices = [
            {'value': '1', 'display_name': 'One'},
            {'value': '2', 'display_name': 'Two'}
        ]
        self.assertIn('choices', field_info)
        self.assertEqual(field_info['choices'], expected_choices)

    def test_get_field_info_with_read_only_many_related_field(self):
        self.many_related_field.read_only = True
        field_info = self.metadata.get_field_info(self.many_related_field)
        self.assertNotIn('choices', field_info)