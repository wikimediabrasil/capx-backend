import os
import time
import requests
from urllib.parse import urlparse
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from skills.models import Skill

METABASE_API_ENDPOINT = "https://metabase.wikibase.cloud/w/api.php"
METABASE_SPARQL_ENDPOINT = "https://metabase.wikibase.cloud/query/sparql"
METAWIKI_API_ENDPOINT = "https://meta.wikimedia.org/w/api.php"

USER_AGENT = "CapX/1.0"

class Command(BaseCommand):
    help = (
        "Sync translations between MetaWiki and MetaBase."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without applying them.",
        )
    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)

        dry_run = options["dry_run"]
        mb_session = None
        mb_token = None
        mw_session = None
        mw_token = None
        if not dry_run:
            mb_session, mb_token = self.login_metabase()
            mw_session, mw_token = self.login_metawiki()

        qids = list(Skill.objects.order_by("pk").values_list("skill_wikidata_item", flat=True))

        metabase = self.fetch_metabase(qids)
        metawiki = self.fetch_metawiki()

        todos = self.diff_translations(qids, metabase, metawiki)
        self.print_todos(todos)
        if not todos and self.verbosity >= 1:
            self.stdout.write("No missing translations found.")

        # Apply changes only where the other side is absent
        if not dry_run and todos:
            applied = 0
            for t in todos:
                qid = t["qid"]
                lang = t["lang"]
                field = t["field"]
                value = t["value"]
                side = t["side"]
                try:
                    if side == "metabase":
                        item_id = self._resolve_metabase_item_id(metabase, qid)
                        if not item_id:
                            self.stderr.write(f"Skip {qid}/{lang} {field}: metabase item not found")
                            continue
                        self.set_metabase_term(mb_session, mb_token, item_id, lang, field, value)
                    elif side == "metawiki":
                        self.set_metawiki_translation(mw_session, mw_token, qid, lang, field, value)
                    else:
                        self.stderr.write(f"Unknown side '{side}' for {qid}/{lang} {field}")
                        continue
                    applied += 1
                    time.sleep(0.2)
                except requests.HTTPError as e:
                    self.stderr.write(f"HTTP error applying {qid}/{lang} {field} to {side}: {e}")
                except Exception as e:
                    self.stderr.write(f"Error applying {qid}/{lang} {field} to {side}: {e}")
            self.stdout.write(f"Applied edits: {applied}")

    def _has_value(self, v):
        return v is not None and str(v).strip() != ""

    def diff_translations(self, qids, metabase, metawiki):
        # Returns a flat list of todo actions describing missing entries
        # [{qid, lang, side, field, value}]
        todos = []
        qid_set = {q for q in qids if q}
        for qid in sorted(qid_set):
            mb_langs = set(metabase.get(qid, {}).keys())
            mw_langs = set(metawiki.get(qid, {}).keys())
            langs = mb_langs | mw_langs
            for lang in sorted(langs):
                mb_terms = metabase.get(qid, {}).get(lang, {})
                mw_terms = metawiki.get(qid, {}).get(lang, {})

                # label
                mb_label = mb_terms.get("label")
                mw_label = mw_terms.get("label")
                if self._has_value(mb_label) and not self._has_value(mw_label):
                    todos.append({
                        "qid": qid,
                        "lang": lang,
                        "side": "metawiki",
                        "field": "label",
                        "value": mb_label,
                    })
                if self._has_value(mw_label) and not self._has_value(mb_label):
                    todos.append({
                        "qid": qid,
                        "lang": lang,
                        "side": "metabase",
                        "field": "label",
                        "value": mw_label,
                    })

                # description
                mb_desc = mb_terms.get("description")
                mw_desc = mw_terms.get("description")
                if self._has_value(mb_desc) and not self._has_value(mw_desc):
                    todos.append({
                        "qid": qid,
                        "lang": lang,
                        "side": "metawiki",
                        "field": "description",
                        "value": mb_desc,
                    })
                if self._has_value(mw_desc) and not self._has_value(mb_desc):
                    todos.append({
                        "qid": qid,
                        "lang": lang,
                        "side": "metabase",
                        "field": "description",
                        "value": mw_desc,
                    })
        return todos

    def print_todos(self, todos):
        if not todos:
            return
        # Group by QID then lang for nicer output
        from collections import defaultdict
        grouped = defaultdict(lambda: defaultdict(list))
        for t in todos:
            grouped[t["qid"]][t["lang"]].append(t)

        total = 0
        for qid in sorted(grouped.keys()):
            self.stdout.write(f"\n== {qid} ==")
            for lang in sorted(grouped[qid].keys()):
                self.stdout.write(f"  [{lang}]")
                for t in grouped[qid][lang]:
                    value_preview = t["value"].replace("\n", " ")
                    if len(value_preview) > 120:
                        value_preview = value_preview[:117] + "..."
                    self.stdout.write(
                        f"    - add to {t['side']}: {t['field']}=\"{value_preview}\""
                    )
                    total += 1
        self.stdout.write(f"\nTotal TODO edits: {total}")

    def parse_entity_id(self, uri: str):
        path = urlparse(uri).path
        if not path:
            return None
        parts = path.strip("/").split("/")
        if parts and parts[-1].startswith("Q"):
            return parts[-1]
        return None

    def _require_setting(self, name):
        val = getattr(settings, name, None)
        if not val:
            raise CommandError(f"Missing required setting: {name}")
        return val

    def login_metabase(self):
        username = self._require_setting("METABASE_USERNAME")
        password = self._require_setting("METABASE_PASSWORD")
        return self._mw_login(METABASE_API_ENDPOINT, username, password)

    def login_metawiki(self):
        username = self._require_setting("METAWIKI_USERNAME")
        password = self._require_setting("METAWIKI_PASSWORD")
        return self._mw_login(METAWIKI_API_ENDPOINT, username, password)

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
            raise CommandError("Failed to get login token.")

        r = s.post(api_endpoint, data={
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json",
        }, timeout=30)
        r.raise_for_status()
        if r.json().get("login", {}).get("result") != "Success":
            raise CommandError(f"Login failed for {api_endpoint}")

        r = s.get(api_endpoint, params={
            "action": "query",
            "meta": "tokens",
            "format": "json",
        }, timeout=30)
        r.raise_for_status()
        csrf = r.json().get("query", {}).get("tokens", {}).get("csrftoken")
        if not csrf:
            raise CommandError("Failed to obtain CSRF token.")
        return s, csrf

    def _resolve_metabase_item_id(self, metabase_map, qid):
        langs = metabase_map.get(qid, {})
        for _, data in langs.items():
            item_id = data.get("metabase_id")
            if item_id:
                return item_id
        return None

    def set_metabase_term(self, session, token, item_id, lang, field, value):
        if field == "label":
            action = "wbsetlabel"
            data = {
                "action": action,
                "id": item_id,
                "language": lang,
                "value": value,
                "token": token,
                "format": "json",
                "assert": "user",
            }
        elif field == "description":
            action = "wbsetdescription"
            data = {
                "action": action,
                "id": item_id,
                "language": lang,
                "value": value,
                "token": token,
                "format": "json",
                "assert": "user",
            }
        else:
            raise ValueError(f"Unsupported field for Metabase: {field}")
    data["maxlag"] = "5"
    r = session.post(METABASE_API_ENDPOINT, data=data, timeout=60)
        r.raise_for_status()
        j = r.json()
        if "error" in j or j.get("success") is False:
            raise CommandError(f"Metabase API error for {item_id}/{lang} {field}: {j}")

    def compose_metawiki_title(self, qid, field, lang):
        base = f"Translations:Module:CapacityExchange/capacities.json/{qid}-{field}"
        return f"{base}/{lang}"

    def set_metawiki_translation(self, session, token, qid, lang, field, value):
        title = self.compose_metawiki_title(qid, field, lang)
        data = {
            "action": "edit",
            "title": title,
            "text": value,
            "summary": f"CapX sync: set {field} ({lang}) for {qid}",
            "format": "json",
            "token": token,
            "assert": "user",
        }
    data["maxlag"] = "5"
    r = session.post(METAWIKI_API_ENDPOINT, data=data, timeout=60)
        r.raise_for_status()
        j = r.json()
        if j.get("edit", {}).get("result") != "Success":
            raise CommandError(f"MetaWiki edit failed for {title}: {j}")

    def fetch_metabase(self, qids):
        item_ids = " ".join(f"'{v}'" for v in qids if v)
        if not item_ids:
            return {}
        # Build VALUES list using a local wd: prefix
        query = f"""PREFIX wbt:<https://metabase.wikibase.cloud/prop/direct/>
            PREFIX wb: <https://metabase.wikibase.cloud/entity/>
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
        headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}
        r = requests.get(METABASE_SPARQL_ENDPOINT, params={"query": query}, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        terms_by_item: dict[str, dict[str, dict[str, str]]] = {}
        for b in data.get("results", {}).get("bindings", []):
            item_uri = b.get("item", {}).get("value")
            item_id = self.parse_entity_id(item_uri) if item_uri else None
            label = b.get("label", {}).get("value")
            description = b.get("description", {}).get("value")
            lang = b.get("language", {}).get("value")
            value = b.get("value", {}).get("value")
            if not item_id or not lang:
                continue
            terms_by_item.setdefault(value, {})[lang] = {
                "label": label,
                "description": description,
                "metabase_id": item_id,
            }
        return terms_by_item

    def fetch_metawiki(self):
        index_params = {
            "action": "query",
            "format": "json",
            "list": "messagecollection",
            "formatversion": "2",
            "mcgroup": "messagebundle-Module:CapacityExchange/capacities.json",
            "mcprop": ""
        }
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(METAWIKI_API_ENDPOINT, params=index_params, timeout=30, headers=headers)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("messagecollection", [])
        translations_by_qid: dict[str, dict[str, dict[str, str]]] = {}
        for page in pages:
            title = page.get("title", "")
            title_params = {
                "action": "query",
                "format": "json",
                "meta": "messagetranslations",
                "formatversion": "2",
                "mttitle": title
            }
            r = requests.get(METAWIKI_API_ENDPOINT, params=title_params, timeout=30, headers=headers)
            r.raise_for_status()
            data = r.json()
            translations = data.get("query", {}).get("messagetranslations", [])
            for entry in translations:
                lang = entry.get("language")
                content = entry.get("translation", "")
                parts = title.split("/")
                if len(parts) < 2:
                    continue
                prev = parts[-2]
                # prev is like 'Q730920-label' or 'Q730920-description'
                if prev.endswith("-label"):
                    qid = prev[:-6]
                    translations_by_qid.setdefault(qid, {}).setdefault(lang, {})["label"] = content.strip()
                elif prev.endswith("-description"):
                    qid = prev[:-12]
                    translations_by_qid.setdefault(qid, {}).setdefault(lang, {})["description"] = content.strip()
        return translations_by_qid
