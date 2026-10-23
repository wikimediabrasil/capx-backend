from dataclasses import dataclass, fields

import requests

from CapX.useragent import get_user_agent

USER_AGENT = get_user_agent("MetabaseCampaignAdapter")


@dataclass
class CampaignDTO:
    metabase_qid: str
    wikidata_qid: str
    url: str
    label_en: str
    description_en: str


class MetabaseCampaignAdapter:
    PROPERTY_MAPPING = {
        # field -> metabase_pid, wikidata_pid
        "wikidata_qid": ("P1", None),
        "url": ("P78", "P856"),
        "label_en": (None, None),
        "description_en": (None, None),
    }
    METABASE_API = (
        "https://metabase.wikibase.cloud/w/rest.php/wikibase/v1/entities/items"
    )
    WIKIDATA_API = "https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch(self, metabase_qid: str) -> CampaignDTO:
        metabase_data = self.fetch_api(self.METABASE_API, metabase_qid)
        if not metabase_data:
            raise ValueError(f"Campaign {metabase_qid} not found in Metabase")

        wikidata_qid = self._extract_property(metabase_data, "P1")

        wikidata_data = {}
        if wikidata_qid:
            wikidata_data = self.fetch_api(self.WIKIDATA_API, wikidata_qid)

        return self._build_dto(metabase_qid, metabase_data, wikidata_qid, wikidata_data)

    def fetch_api(self, endpoint, qid: str) -> dict:
        url = f"{endpoint}/{qid}"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {}

    def _extract_property(self, data: dict, prop_id: str) -> str:
        statements = data.get("statements", {})
        prop_statements = statements.get(prop_id, [])
        for stmt in prop_statements:
            value = stmt.get("value", {})
            if value.get("type") == "value":
                content = value.get("content")
                if isinstance(content, str):
                    return content
        return ""

    def _extract_label_en(self, data: dict) -> str:
        return data.get("labels", {}).get("en", "")

    def _extract_description_en(self, data: dict) -> str:
        return data.get("descriptions", {}).get("en", "")

    def _get_field_value(
        self, field_name: str, metabase_data: dict, wikidata_data: dict
    ) -> str:
        metabase_prop, wikidata_prop = self.PROPERTY_MAPPING.get(
            field_name,
            (None, None),
        )

        if wikidata_prop and wikidata_data:
            val = self._extract_property(wikidata_data, wikidata_prop)
            if val:
                return val

        if metabase_prop:
            return self._extract_property(metabase_data, metabase_prop)

        return ""

    def _build_dto(
        self,
        metabase_qid: str,
        metabase: dict,
        wikidata_qid: str,
        wikidata: dict,
    ) -> CampaignDTO:
        vals = {}
        for field in fields(CampaignDTO):
            name = field.name
            if name == "metabase_qid":
                vals[name] = metabase_qid
            elif name == "wikidata_qid":
                vals[name] = wikidata_qid
            elif name == "label_en":
                vals[name] = self._extract_label_en(metabase)
            elif name == "description_en":
                vals[name] = self._extract_description_en(metabase)
            else:
                vals[name] = self._get_field_value(name, metabase, wikidata)

        return CampaignDTO(**vals)
