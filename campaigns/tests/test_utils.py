from typing import ClassVar
from unittest.mock import MagicMock, patch

from django.test import TestCase

from campaigns.utils import CampaignDTO, MetabaseCampaignAdapter


class TestMetabaseCampaignAdapter(TestCase):
    def setUp(self):
        self.client = MetabaseCampaignAdapter()

    METABASE_RESPONSE: ClassVar[dict] = {
        "type": "item",
        "labels": {
            "sv": "Wiki Loves Earth",
            "en": "Wiki Loves Earth",
            "it": "Wiki Loves Earth",
        },
        "descriptions": {
            "en": "photographic competition",
            "it": "concorso fotografico",
        },
        "aliases": {
            "en": ["WLE"],
            "mul": ["WLE"],
        },
        "statements": {
            "P5": [
                {
                    "id": "Q22601$4c5ecba8-4013-11ff-ab49-d108c96f5d46",
                    "rank": "normal",
                    "qualifiers": [],
                    "references": [],
                    "property": {"id": "P5", "data_type": "wikibase-item"},
                    "value": {"type": "value", "content": "Q142"},
                }
            ],
            "P1": [
                {
                    "id": "Q22601$cc568bc2-42aa-f011-3201-3f3891c61f5a",
                    "rank": "normal",
                    "qualifiers": [],
                    "references": [],
                    "property": {"id": "P1", "data_type": "external-id"},
                    "value": {"type": "value", "content": "Q16695775"},
                }
            ],
            "P35": [
                {
                    "id": "Q22601$fc6ecf5f-44dc-25e1-79d4-fb34f5d3c565",
                    "rank": "normal",
                    "qualifiers": [],
                    "references": [],
                    "property": {"id": "P35", "data_type": "wikibase-item"},
                    "value": {"type": "value", "content": "Q22602"},
                }
            ],
            "P78": [
                {
                    "id": "Q22601$p78-1",
                    "rank": "normal",
                    "qualifiers": [],
                    "references": [],
                    "property": {"id": "P78", "data_type": "url"},
                    "value": {
                        "type": "value",
                        "content": "https://metabase.wikiloves.example.org",
                    },
                }
            ],
        },
        "sitelinks": {},
        "id": "Q22601",
    }

    WIKIDATA_RESPONSE: ClassVar[dict] = {
        "type": "item",
        "labels": {
            "en": "Wiki Loves Earth",
            "pt": "Wiki Loves Earth",
        },
        "descriptions": {
            "en": "annual international photographic competition for protected areas of nature conservation and natural heritage",
        },
        "statements": {
            "P856": [
                {
                    "id": "Q16695775$p856-1",
                    "rank": "normal",
                    "qualifiers": [],
                    "references": [],
                    "property": {"id": "P856", "data_type": "url"},
                    "value": {
                        "type": "value",
                        "content": "http://www.wikilovesearth.org",
                    },
                }
            ],
        },
        "sitelinks": {
            "enwiki": {
                "title": "Wiki Loves Earth",
                "badges": [],
                "url": "https://en.wikipedia.org/wiki/Wiki_Loves_Earth",
            }
        },
        "id": "Q16695775",
    }

    @patch("campaigns.utils.requests.Session.get")
    def test_fetch_with_wikidata(self, mock_get):
        metabase_response = MagicMock()
        metabase_response.status_code = 200
        metabase_response.json.return_value = self.METABASE_RESPONSE

        wikidata_response = MagicMock()
        wikidata_response.status_code = 200
        wikidata_response.json.return_value = self.WIKIDATA_RESPONSE

        mock_get.side_effect = [metabase_response, wikidata_response]

        dto = self.client.fetch("Q22601")

        self.assertIsInstance(dto, CampaignDTO)
        self.assertEqual(dto.metabase_qid, "Q22601")
        self.assertEqual(dto.wikidata_qid, "Q16695775")
        self.assertEqual(dto.url, "http://www.wikilovesearth.org")
        self.assertEqual(dto.label_en, "Wiki Loves Earth")
        self.assertEqual(dto.description_en, "photographic competition")

        self.assertEqual(mock_get.call_count, 2)
        self.assertIn("metabase.wikibase.cloud", mock_get.call_args_list[0][0][0])
        self.assertIn("wikidata.org", mock_get.call_args_list[1][0][0])

    @patch("campaigns.utils.requests.Session.get")
    def test_fetch_without_wikidata(self, mock_get):
        metabase_response = MagicMock()
        metabase_response.status_code = 200
        data = self.METABASE_RESPONSE.copy()
        data["statements"] = {k: v for k, v in data["statements"].items() if k != "P1"}
        metabase_response.json.return_value = data

        mock_get.return_value = metabase_response

        dto = self.client.fetch("Q22601")

        self.assertEqual(dto.metabase_qid, "Q22601")
        self.assertEqual(dto.wikidata_qid, "")
        self.assertEqual(dto.url, "https://metabase.wikiloves.example.org")
        self.assertEqual(dto.label_en, "Wiki Loves Earth")
        self.assertEqual(dto.description_en, "photographic competition")

        self.assertEqual(mock_get.call_count, 1)

    @patch("campaigns.utils.requests.Session.get")
    def test_fetch_wikidata_missing_url_fallback_to_metabase(self, mock_get):
        metabase_response = MagicMock()
        metabase_response.status_code = 200
        metabase_response.json.return_value = self.METABASE_RESPONSE

        wikidata_response = MagicMock()
        wikidata_response.status_code = 200
        wikidata_response.json.return_value = {
            "type": "item",
            "labels": {"en": {"value": "Wikidata Label"}},
            "descriptions": {"en": {"value": "Wikidata Description"}},
            "statements": {},
            "sitelinks": {},
            "id": "Q16695775",
        }

        mock_get.side_effect = [metabase_response, wikidata_response]

        dto = self.client.fetch("Q22601")

        self.assertEqual(dto.url, "https://metabase.wikiloves.example.org")
        self.assertEqual(dto.label_en, "Wiki Loves Earth")
        self.assertEqual(dto.description_en, "photographic competition")

    @patch("campaigns.utils.requests.Session.get")
    def test_fetch_metabase_not_found(self, mock_get):
        metabase_response = MagicMock()
        metabase_response.status_code = 404
        mock_get.return_value = metabase_response

        with self.assertRaises(ValueError) as cm:
            self.client.fetch("Q99999")

        self.assertIn("not found in Metabase", str(cm.exception))

    @patch("campaigns.utils.requests.Session.get")
    def test_fetch_metabase_network_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("Connection failed")

        with self.assertRaises(ValueError) as cm:
            self.client.fetch("Q22601")

        self.assertIn("not found in Metabase", str(cm.exception))

    @patch("campaigns.utils.requests.Session.get")
    def test_fetch_wikidata_network_error_fallback(self, mock_get):
        import requests

        metabase_response = MagicMock()
        metabase_response.status_code = 200
        metabase_response.json.return_value = self.METABASE_RESPONSE

        mock_get.side_effect = [
            metabase_response,
            requests.RequestException("Wikidata down"),
        ]

        dto = self.client.fetch("Q22601")

        self.assertEqual(dto.metabase_qid, "Q22601")
        self.assertEqual(dto.wikidata_qid, "Q16695775")
        self.assertEqual(dto.url, "https://metabase.wikiloves.example.org")
        self.assertEqual(dto.label_en, "Wiki Loves Earth")
        self.assertEqual(dto.description_en, "photographic competition")

    @patch("campaigns.utils.requests.Session.get")
    def test_fetch_wikidata_404_fallback(self, mock_get):
        metabase_response = MagicMock()
        metabase_response.status_code = 200
        metabase_response.json.return_value = self.METABASE_RESPONSE

        wikidata_response = MagicMock()
        wikidata_response.status_code = 404
        mock_get.side_effect = [metabase_response, wikidata_response]

        dto = self.client.fetch("Q22601")

        self.assertEqual(dto.wikidata_qid, "Q16695775")
        self.assertEqual(dto.url, "https://metabase.wikiloves.example.org")
        self.assertEqual(dto.label_en, "Wiki Loves Earth")


if __name__ == "__main__":
    import unittest

    unittest.main()
