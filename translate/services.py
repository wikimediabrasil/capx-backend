import json
import os
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from django.conf import settings
from CapX.useragent import get_user_agent
from requests_oauthlib import OAuth1Session

METABASE_API_ENDPOINT = "https://metabase.wikibase.cloud/w/api.php"
METABASE_SPARQL_ENDPOINT = "https://metabase.wikibase.cloud/query/sparql"
USER_AGENT = get_user_agent("Translate")


class MetabaseClient:
    """Minimal client for Wikibase (Metabase) to fetch and edit terms."""

    def __init__(self):
        self._session: Optional[requests.Session] = None
        self._token: Optional[str] = None
        self.metabase_ids: Dict[str, str] = {}

    # --- Auth
    def login_bot(self):
        """Login as CapacityExchangeBot using credentials from settings_local."""
        username = os.environ.get("METABASE_USERNAME")
        password = os.environ.get("METABASE_PASSWORD")
        if not username or not password:
            raise RuntimeError("Missing METABASE_USERNAME/METABASE_PASSWORD in settings_local.py or env")
        self._session, self._token = self._mw_login(METABASE_API_ENDPOINT, username, password)
        return self

    def login_user_oauth(self, access_token: str, access_secret: str):
        """Use a user's Metabase OAuth credentials to authenticate requests.
        Requires environment variables METABASE_OAUTH_CONSUMER_KEY and METABASE_OAUTH_CONSUMER_SECRET.
        """
        consumer_key = os.environ.get("METABASE_OAUTH_CONSUMER_KEY")
        consumer_secret = os.environ.get("METABASE_OAUTH_CONSUMER_SECRET")
        if not consumer_key or not consumer_secret:
            raise RuntimeError("Missing METABASE_OAUTH_CONSUMER_KEY/SECRET env vars")
        sess = OAuth1Session(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_secret,
        )
        # Fetch CSRF token with the OAuth session
        r = sess.get(METABASE_API_ENDPOINT, params={
            "action": "query",
            "meta": "tokens",
            "format": "json",
        }, timeout=30)
        r.raise_for_status()
        csrf = r.json().get("query", {}).get("tokens", {}).get("csrftoken")
        if not csrf:
            raise RuntimeError("Failed to obtain CSRF token via OAuth session.")
        self._session, self._token = sess, csrf
        return self

    def _mw_login(self, api_endpoint, username, password):
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})
        r = s.get(api_endpoint, params={
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        }, timeout=30)
        r.raise_for_status()
        login_token = r.json().get("query", {}).get("tokens", {}).get("logintoken")
        if not login_token:
            raise RuntimeError("Failed to get login token.")

        r = s.post(api_endpoint, data={
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json",
        }, timeout=30)
        r.raise_for_status()
        if r.json().get("login", {}).get("result") != "Success":
            raise RuntimeError("Login failed for Metabase")

        r = s.get(api_endpoint, params={
            "action": "query",
            "meta": "tokens",
            "format": "json",
        }, timeout=30)
        r.raise_for_status()
        csrf = r.json().get("query", {}).get("tokens", {}).get("csrftoken")
        if not csrf:
            raise RuntimeError("Failed to obtain CSRF token.")
        return s, csrf

    def _parse_entity_id(self, uri: str | None):
        try:
            path = urlparse(uri).path
        except Exception:
            return None
        if not path:
            return None
        parts = path.strip("/").split("/")
        if parts and parts[-1].startswith("Q"):
            return parts[-1]
        return None

    def _post_action(self, data: dict, timeout: int = 60):
        if not self._session or not self._token:
            raise RuntimeError("MetabaseClient not logged in")
        payload = {
            **data,
            "format": "json",
            "token": self._token,
            "assert": "user",
            "maxlag": "5",
        }
        r = self._session.post(METABASE_API_ENDPOINT, data=payload, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        if "error" in j or j.get("success") is False:
            raise RuntimeError(f"Metabase API error for action {data.get('action')}: {j}")
        return j

    def _item_datavalue(self, qid: str):
        if not qid or not qid.startswith("Q"):
            raise ValueError(f"Invalid item id: {qid}")
        return {
            "entity-type": "item",
            "numeric-id": int(qid[1:]),
            "id": qid,
        }

    def _create_wikibase_item(self, label: str | None, description: str | None, lang: str, summary: str):
        data_obj = {}
        if label:
            data_obj["labels"] = {lang: {"language": lang, "value": label}}
        if description:
            data_obj["descriptions"] = {lang: {"language": lang, "value": description}}

        payload = {
            "action": "wbeditentity",
            "new": "item",
            "data": json.dumps(data_obj, ensure_ascii=False),
            "summary": summary,
        }
        result = self._post_action(payload)
        entity_id = (result.get("entity") or {}).get("id")
        if not entity_id:
            raise RuntimeError("Metabase create item did not return entity id")
        return entity_id

    def _create_claim(self, entity_id: str, prop: str, value, summary: str):
        payload = {
            "action": "wbcreateclaim",
            "entity": entity_id,
            "property": prop,
            "snaktype": "value",
            "value": json.dumps(value, ensure_ascii=False),
            "summary": summary,
        }
        self._post_action(payload)

    def _find_index_term_by_wikidata_qid(self, wikidata_qid: str):
        query = f"""PREFIX wbt:<https://metabase.wikibase.cloud/prop/direct/>
            SELECT ?item WHERE {{
                VALUES ?value {{ \"{wikidata_qid}\" }}
                ?item wbt:P1 ?value.
            }}
            LIMIT 1"""
        headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}
        r = requests.get(METABASE_SPARQL_ENDPOINT, params={"query": query}, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        for binding in data.get("results", {}).get("bindings", []):
            entity_id = self._parse_entity_id(binding.get("item", {}).get("value"))
            if entity_id:
                return entity_id
        return None

    def _fetch_wikidata_terms(self, wikidata_qid: str, lang: str):
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_qid}.json"
        headers = {"User-Agent": USER_AGENT}
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
        except requests.RequestException:
            return {}

        entity = (r.json().get("entities") or {}).get(wikidata_qid) or {}
        labels = entity.get("labels") or {}
        descriptions = entity.get("descriptions") or {}
        preferred_langs = [lang, "en"] if lang != "en" else ["en"]

        label = None
        description = None
        for preferred in preferred_langs:
            if not label:
                label = ((labels.get(preferred) or {}).get("value"))
            if not description:
                description = ((descriptions.get(preferred) or {}).get("value"))

        return {
            "label": label,
            "description": description,
        }

    # --- Fetch
    def fetch_map_and_terms(self, qids):
        """
        Returns a mapping: {
          qid: { lang: { 'label': str|None, 'description': str|None, 'metabase_id': 'Q123' } }
        }
        Also populates self.metabase_ids for quick lookup.
        """
        item_ids = " ".join(f"'{v}'" for v in qids if v)
        if not item_ids:
            return {}
        headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}
        # First, map value (Wikidata QID) -> Metabase Item id
        map_query = f"""PREFIX wbt:<https://metabase.wikibase.cloud/prop/direct/>
            PREFIX wb: <https://metabase.wikibase.cloud/entity/>
            SELECT DISTINCT ?item ?value WHERE {{
                VALUES ?value {{ {item_ids} }}
                ?item wbt:P5 wb:Q34531.
                ?item wbt:P67/wbt:P1 ?value.
            }}"""
        r = requests.get(METABASE_SPARQL_ENDPOINT, params={"query": map_query}, headers=headers, timeout=60)
        r.raise_for_status()
        map_data = r.json()
        value_to_item = {}
        for b in map_data.get("results", {}).get("bindings", []):
            item_uri = b.get("item", {}).get("value")
            value = b.get("value", {}).get("value")
            item_id = self._parse_entity_id(item_uri) if item_uri else None
            if item_id and value:
                value_to_item[value] = item_id
        self.metabase_ids = value_to_item

        # Then fetch terms
        query = f"""PREFIX wbt:<https://metabase.wikibase.cloud/prop/direct/>
            PREFIX wb: <https://metabase.wikibase.cloud/entity/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX schema: <http://schema.org/>
            SELECT ?item ?value ?language (SAMPLE(?label) AS ?label) (SAMPLE(?description) AS ?description) WHERE {{  
                VALUES ?value {{ {item_ids} }}
                ?item wbt:P5 wb:Q34531.
                ?item wbt:P67/wbt:P1 ?value.  
                {{
                    ?item rdfs:label ?label.
                    BIND(LANG(?label) AS ?language)
                }}
                UNION
                {{
                    ?item schema:description ?description.
                    BIND(LANG(?description) AS ?language)
                }}
            }}
            GROUP BY ?item ?value ?language
            ORDER BY ?language
            """
        r = requests.get(METABASE_SPARQL_ENDPOINT, params={"query": query}, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        terms_by_value: Dict[str, Dict[str, Dict[str, str]]] = {}
        for b in data.get("results", {}).get("bindings", []):
            item_uri = b.get("item", {}).get("value")
            item_id = self._parse_entity_id(item_uri) if item_uri else None
            label = b.get("label", {}).get("value")
            description = b.get("description", {}).get("value")
            lang = b.get("language", {}).get("value")
            value = b.get("value", {}).get("value")
            if not item_id or not lang or not value:
                continue
            terms_by_value.setdefault(value, {})[lang] = {
                "label": label,
                "description": description,
                "metabase_id": item_id,
            }
        return terms_by_value

    # --- Edits
    def set_term(self, metabase_id: str, lang: str, field: str, value: str, editor_username: str):
        if field not in ("label", "description"):
            raise ValueError("field must be 'label' or 'description'")
        if not self._session or not self._token:
            raise RuntimeError("MetabaseClient not logged in")
        action = "wbsetlabel" if field == "label" else "wbsetdescription"
        data = {
            "action": action,
            "id": metabase_id,
            "language": lang,
            "value": value,
            "token": self._token,
            "summary": f"CapX translate: set {field} ({lang}) by {editor_username}",
            "format": "json",
            "assert": "user",
            "maxlag": "5",
        }
        r = self._session.post(METABASE_API_ENDPOINT, data=data, timeout=60)
        r.raise_for_status()
        j = r.json()
        if "error" in j or j.get("success") is False:
            raise RuntimeError(f"Metabase API error for {metabase_id}/{lang} {field}: {j}")

    def create_item(
        self,
        label: str,
        description: str | None = None,
        lang: str = "en",
        wikidata_qid: str | None = None,
        editor_username: str = "admin",
        skill_pk: int | None = None,
    ) -> Dict[str, str]:
        """Create or reuse index term and create the related CapX capacity item.

        Returns a dictionary with both created/resolved ids:
        {
            "index_term_id": "Q123",
            "capacity_id": "Q456",
        }
        """
        if not self._session or not self._token:
            raise RuntimeError("MetabaseClient not logged in")
        if not wikidata_qid:
            raise RuntimeError("wikidata_qid is required to create Metabase items")

        index_term_id = self._find_index_term_by_wikidata_qid(wikidata_qid)
        if not index_term_id:
            wikidata_terms = self._fetch_wikidata_terms(wikidata_qid, lang)
            index_label = wikidata_terms.get("label") or label or wikidata_qid
            index_description = wikidata_terms.get("description") or description

            index_term_id = self._create_wikibase_item(
                label=index_label,
                description=index_description,
                lang=lang,
                summary=f"CapX skill create: index term for {wikidata_qid} by {editor_username}",
            )
            self._create_claim(
                entity_id=index_term_id,
                prop="P5",
                value=self._item_datavalue("Q12"),
                summary=f"CapX skill create: set P5=Q12 for {index_term_id} by {editor_username}",
            )
            self._create_claim(
                entity_id=index_term_id,
                prop="P1",
                value=wikidata_qid,
                summary=f"CapX skill create: set P1={wikidata_qid} for {index_term_id} by {editor_username}",
            )

        capacity_id = self._create_wikibase_item(
            label=label,
            description=description,
            lang=lang,
            summary=f"CapX skill create: capacity for {wikidata_qid} by {editor_username}",
        )
        self._create_claim(
            entity_id=capacity_id,
            prop="P5",
            value=self._item_datavalue("Q34531"),
            summary=f"CapX skill create: set P5=Q34531 for {capacity_id} by {editor_username}",
        )
        self._create_claim(
            entity_id=capacity_id,
            prop="P67",
            value=self._item_datavalue(index_term_id),
            summary=f"CapX skill create: set P67={index_term_id} for {capacity_id} by {editor_username}",
        )
        if skill_pk is not None:
            self._create_claim(
                entity_id=capacity_id,
                prop="P91",
                value=str(skill_pk),
                summary=f"CapX skill create: set P91={skill_pk} for {capacity_id} by {editor_username}",
            )

        return {
            "index_term_id": index_term_id,
            "capacity_id": capacity_id,
        }
        


def build_capacity_list(terms_by_qid: Dict[str, Dict[str, Dict[str, str]]], lang: str, fallback: str = 'en'):
    """
    Build a flattened list suitable for UI/API consumption.
    Each item: { qid, metabase_id, lang, label, description, fallback_label, fallback_description }

    If the chosen fallback is missing a label/description for a given item,
    English (en) is used as a secondary fallback for that specific field.
    """
    items = []
    for qid, lang_map in terms_by_qid.items():
        current = lang_map.get(lang, {})
        fb = lang_map.get(fallback, {})
        fb_en = lang_map.get('en', {}) if fallback != 'en' else {}
        metabase_id = (current or fb or fb_en or {}).get('metabase_id')
        fallback_label = (fb or {}).get('label')
        fallback_description = (fb or {}).get('description')
        if not fallback_label:
            fallback_label = (fb_en or {}).get('label')
        if not fallback_description:
            fallback_description = (fb_en or {}).get('description')
        items.append({
            'qid': qid,
            'metabase_id': metabase_id,
            'lang': lang,
            'label': (current or {}).get('label'),
            'description': (current or {}).get('description'),
            'fallback_label': fallback_label,
            'fallback_description': fallback_description,
        })
    return items
