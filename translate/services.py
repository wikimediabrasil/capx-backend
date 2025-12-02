import json
import os
from datetime import datetime
from typing import Dict, Optional

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
            raise RuntimeError("Missing CAPX_BOT_USERNAME/CAPX_BOT_PASSWORD in settings_local.py or env")
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

    # --- Helpers
    def _parse_entity_id(self, uri: str) -> Optional[str]:
        try:
            path = uri.split("/entity/")[-1]
            return path if path.startswith("Q") else None
        except Exception:
            return None


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
