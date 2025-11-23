import os
import re
import time
import json
from datetime import datetime
import requests
from urllib.parse import urlparse
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from bugs.models import Bug
from skills.models import Skill
from collections import defaultdict

METABASE_API_ENDPOINT = "https://metabase.wikibase.cloud/w/api.php"
METABASE_SPARQL_ENDPOINT = "https://metabase.wikibase.cloud/query/sparql"
METAWIKI_API_ENDPOINT = "https://meta.wikimedia.org/w/api.php"

from CapX.useragent import get_user_agent
USER_AGENT = get_user_agent("SyncTranslations")

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

        mb_session, mb_token, mw_session, mw_token = self._init_sessions(dry_run)
        qids = list(Skill.objects.order_by("pk").values_list("skill_wikidata_item", flat=True))
        metabase = self.fetch_metabase(qids)
        metawiki = self.fetch_metawiki()

        todos = self.diff_translations(qids, metabase, metawiki)
        self.print_todos(todos)
        if not todos and self.verbosity >= 1:
            self.stdout.write("No missing translations found.")

        if not dry_run and todos:
            applied = self._apply_todos(todos, mb_session, mb_token, mw_session, mw_token)
            self.stdout.write(f"Applied edits: {applied}")

        self._process_mismatches(metabase, metawiki, dry_run, mb_session, mb_token, mw_session, mw_token)

    def _init_sessions(self, dry_run):
        mb_session = mb_token = mw_session = mw_token = None
        if not dry_run:
            mb_session, mb_token = self.login_metabase()
            mw_session, mw_token = self.login_metawiki()
        return mb_session, mb_token, mw_session, mw_token

    def _apply_todos(self, todos, mb_session, mb_token, mw_session, mw_token):
        applied = 0
        for t in todos:
            qid = t["qid"]
            lang = t["lang"]
            field = t["field"]
            value = t["value"]
            side = t["side"]
            metabase_id = t["metabase_id"]
            try:
                if side == "metabase":
                    self.set_metabase_term(mb_session, mb_token, metabase_id, lang, field, value, qid)
                elif side == "metawiki":
                    self.set_metawiki_translation(mw_session, mw_token, qid, lang, field, value, metabase_id)
                else:
                    self.stderr.write(f"Unknown side '{side}' for {qid}/{lang} {field}")
                    continue
                applied += 1
                time.sleep(10)
            except requests.HTTPError as e:
                self.stderr.write(f"HTTP error applying {qid}/{lang} {field} to {side}: {e}")
            except Exception as e:
                self.stderr.write(f"Error applying {qid}/{lang} {field} to {side}: {e}")
        return applied

    def _process_mismatches(self, metabase, metawiki, dry_run, mb_session=None, mb_token=None, mw_session=None, mw_token=None):
        """
        For each mismatch (both sides have values but differ), pick the most recently
        updated source and sync the other side. If we cannot determine recency for an
        entry, fall back to filing a bug (one bug per QID, containing unresolved entries).
        """
        mismatches = self.find_mismatches(metabase, metawiki)
        if not mismatches:
            if self.verbosity >= 1:
                self.stdout.write("No mismatches found.")
            return

        total = 0
        resolved = 0
        bug_created = 0
        skipped_existing_bug = 0

        for qid, entries in mismatches.items():
            unresolved_for_bug = []
            metabase_id = self.get_metabase_id_for_qid(metabase, qid)
            if self.verbosity >= 2:
                self.stdout.write(f"Processing mismatches for {qid} (Metabase item: {metabase_id or 'unknown'})...")

            for e in entries:
                total += 1
                lang = e["lang"]
                field = e["field"]  # 'label' | 'description'
                mb_value = e.get("metabase")
                mw_value = e.get("metawiki")

                try:
                    t_mw = self.get_metawiki_term_last_modified(qid, field, lang, session=mw_session)
                except Exception as ex:
                    t_mw = None
                    if self.verbosity >= 2:
                        self.stderr.write(f"Failed to fetch MetaWiki timestamp for {qid}/{lang} {field}: {ex}")

                try:
                    t_mb = self.get_metabase_term_last_modified(metabase_id, field, lang, session=mb_session)
                except Exception as ex:
                    t_mb = None
                    if self.verbosity >= 2:
                        self.stderr.write(f"Failed to fetch Metabase timestamp for {qid}/{lang} {field}: {ex}")

                decision = None
                if t_mw and t_mb:
                    decision = "metawiki" if t_mw > t_mb else "metabase"
                elif t_mw and not t_mb:
                    decision = "metawiki"
                elif t_mb and not t_mw:
                    decision = "metabase"

                if decision == "metawiki":
                    # Metawiki newer -> push to Metabase
                    if self.verbosity >= 1:
                        when = t_mw.isoformat() if t_mw else "unknown"
                        self.stdout.write(f"[{qid}/{lang} {field}] MetaWiki is newer ({when}); syncing to Metabase...")
                    if not dry_run and metabase_id:
                        try:
                            self.set_metabase_term(mb_session, mb_token, metabase_id, lang, field, mw_value, qid)
                            resolved += 1
                            time.sleep(10)
                        except requests.HTTPError as http_ex:
                            self.stderr.write(f"HTTP error setting Metabase term for {qid}/{lang} {field}: {http_ex}")
                            unresolved_for_bug.append(e)
                        except Exception as ex:
                            self.stderr.write(f"Error setting Metabase term for {qid}/{lang} {field}: {ex}")
                            unresolved_for_bug.append(e)
                    else:
                        # Dry run or missing metabase_id
                        resolved += 1 if dry_run else 0
                        if dry_run and self.verbosity >= 2:
                            self.stdout.write(f"DRY-RUN: would set Metabase {field} ({lang}) for {qid} -> '{mw_value}'")
                        if not metabase_id and not dry_run:
                            unresolved_for_bug.append(e)
                elif decision == "metabase":
                    # Metabase newer -> push to MetaWiki
                    if self.verbosity >= 1:
                        when = t_mb.isoformat() if t_mb else "unknown"
                        self.stdout.write(f"[{qid}/{lang} {field}] Metabase is newer ({when}); syncing to MetaWiki...")
                    if not dry_run:
                        try:
                            self.set_metawiki_translation(mw_session, mw_token, qid, lang, field, mb_value, metabase_id)
                            resolved += 1
                            time.sleep(10)
                        except requests.HTTPError as http_ex:
                            self.stderr.write(f"HTTP error setting MetaWiki translation for {qid}/{lang} {field}: {http_ex}")
                            unresolved_for_bug.append(e)
                        except Exception as ex:
                            self.stderr.write(f"Error setting MetaWiki translation for {qid}/{lang} {field}: {ex}")
                            unresolved_for_bug.append(e)
                    else:
                        resolved += 1
                        if self.verbosity >= 2:
                            self.stdout.write(f"DRY-RUN: would set MetaWiki {field} ({lang}) for {qid} -> '{mb_value}'")
                else:
                    # Cannot decide which is newer
                    if self.verbosity >= 1:
                        self.stdout.write(f"[{qid}/{lang} {field}] Could not determine recency; will file a bug entry.")
                    unresolved_for_bug.append(e)

            # Create bug only for unresolved entries of this QID
            if unresolved_for_bug:
                if self._skip_existing_bug(qid):
                    skipped_existing_bug += 1
                else:
                    if self.verbosity >= 2:
                        self.stdout.write(f"Creating bug for {qid} with {len(unresolved_for_bug)} unresolved mismatches...")
                    if not dry_run:
                        self.ensure_bug_for_mismatches(qid, unresolved_for_bug, dry_run=False)
                    bug_created += 1

        self.stdout.write(
            f"Mismatch resolution: total={total}, resolved={resolved}, bugs_created={bug_created}, existing_bugs_skipped={skipped_existing_bug}"
        )

    def _parse_ts(self, ts: str):
        if not ts:
            return None
        try:
            # Convert MW '...Z' to ISO with timezone
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return None

    def get_metawiki_term_last_modified(self, qid: str, field: str, lang: str, session: requests.Session | None = None):
        """Return the timestamp (datetime) of the latest edit to the MetaWiki translation page."""
        title = self.compose_metawiki_title(qid, field, lang)
        s = session or requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})
        params = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "titles": title,
            "rvlimit": 1,
            "rvprop": "timestamp",
            "formatversion": "2",
        }
        r = s.get(METAWIKI_API_ENDPOINT, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        pages = j.get("query", {}).get("pages", [])
        if not pages:
            return None
        revs = pages[0].get("revisions", [])
        if not revs:
            return None
        return self._parse_ts(revs[0].get("timestamp"))

    def get_metabase_term_last_modified(self, metabase_id: str | None, field: str, lang: str, session: requests.Session | None = None, max_revisions: int = 400):
        """
        Return the timestamp (datetime) when the current label/description value for a language
        on the Wikibase item was introduced (i.e., the latest change time for that term).
        If metabase_id is None or value not present, returns None.
        """
        if not metabase_id:
            return None

        s = session or requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})

        # First, get the current term value to compare against history
        r = s.get(METABASE_API_ENDPOINT, params={
            "action": "wbgetentities",
            "format": "json",
            "ids": metabase_id,
            "props": f"{field}s",
            "languages": lang,
        }, timeout=30)
        r.raise_for_status()
        j = r.json()
        entity = j.get("entities", {}).get(metabase_id, {})
        terms = entity.get(f"{field}s", {})
        cur_term = terms.get(lang)
        cur_value = (cur_term or {}).get("value")
        if not cur_value:
            return None

        # Walk revisions of the item page to find when this value first appeared
        title = f"Item:{metabase_id}"
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "titles": title,
            "rvslots": "main",
            "rvprop": "ids|timestamp|content",
            # default order: newest first
            "rvlimit": "50",
        }
        processed = 0
        last_equal_ts = None
        cont = None

        def extract_value_from_rev(rev):
            slots = rev.get("slots", {})
            main = slots.get("main", {})
            content = main.get("*") or main.get("content") or rev.get("*")
            if not content:
                return None
            try:
                data = json.loads(content)
            except Exception:
                return None
            d = data.get(f"{field}s", {})
            v = d.get(lang, {})
            return v.get("value")

        while True:
            params2 = dict(params)
            if cont:
                params2["rvcontinue"] = cont
            r = s.get(METABASE_API_ENDPOINT, params=params2, timeout=60)
            r.raise_for_status()
            j = r.json()
            pages = j.get("query", {}).get("pages", [])
            if not pages:
                break
            revs = pages[0].get("revisions", [])
            for rev in revs:
                processed += 1
                ts = self._parse_ts(rev.get("timestamp"))
                val = extract_value_from_rev(rev)
                if val == cur_value:
                    last_equal_ts = ts
                else:
                    # We crossed the boundary where term changed: the next newer revision
                    # (which we've already seen) is when the current value first appeared.
                    return last_equal_ts
                if processed >= max_revisions:
                    return last_equal_ts

            cont = j.get("continue", {}).get("rvcontinue")
            if not cont:
                break

        return last_equal_ts

    def _skip_existing_bug(self, qid):
        existing = Bug.objects.filter(title=self.bug_title_for_qid(qid)).first()
        return existing is not None

    def _has_value(self, v):
        return v is not None and str(v).strip() != ""

    def diff_translations(self, qids, metabase, metawiki):
        # Returns a flat list of todo actions describing missing entries
        # [{qid, lang, side, field, value}]
        def add_todo_if_missing(qid, lang, metabase_id, mb_terms, mw_terms, field, todos):
            mb_value = mb_terms.get(field)
            mw_value = mw_terms.get(field)
            if self._has_value(mb_value) and not self._has_value(mw_value):
                todos.append({
                    "qid": qid,
                    "lang": lang,
                    "side": "metawiki",
                    "metabase_id": metabase_id,
                    "field": field,
                    "value": mb_value,
                })
            if self._has_value(mw_value) and not self._has_value(mb_value):
                todos.append({
                    "qid": qid,
                    "lang": lang,
                    "side": "metabase",
                    "metabase_id": metabase_id,
                    "field": field,
                    "value": mw_value,
                })

        todos = []
        qid_set = {q for q in qids if q}
        for qid in sorted(qid_set):
            metabase_id = self.get_metabase_id_for_qid(metabase, qid)
            mb_langs = set(metabase.get(qid, {}).keys())
            mw_langs = set(metawiki.get(qid, {}).keys())
            langs = mb_langs | mw_langs
            for lang in sorted(langs):
                mb_terms = metabase.get(qid, {}).get(lang, {})
                mw_terms = metawiki.get(qid, {}).get(lang, {})
                for field in ("label", "description"):
                    add_todo_if_missing(qid, lang, metabase_id, mb_terms, mw_terms, field, todos)
        return todos

    def print_todos(self, todos):
        if not todos:
            return
        # Group by QID then lang for nicer output
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
        username = os.environ.get("METABASE_USERNAME")
        password = os.environ.get("METABASE_PASSWORD")
        return self._mw_login(METABASE_API_ENDPOINT, username, password)

    def login_metawiki(self):
        username = os.environ.get("METAWIKI_USERNAME")
        password = os.environ.get("METAWIKI_PASSWORD")
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

    def set_metabase_term(self, session, token, metabase_id, lang, field, value, qid):
        if field == "label":
            action = "wbsetlabel"
            data = {
                "action": action,
                "id": metabase_id,
                "language": lang,
                "value": value,
                "token": token,
                "summary": f"CapX sync: set {field} ({lang}) for {metabase_id}, imported from https://meta.wikimedia.org/wiki/Translations:Module:CapacityExchange/capacities.json/{qid}-{field}/{lang}",
                "format": "json",
                "assert": "user",
            }
        elif field == "description":
            action = "wbsetdescription"
            data = {
                "action": action,
                "id": metabase_id,
                "language": lang,
                "value": value,
                "token": token,
                "summary": f"CapX sync: set {field} ({lang}) for {metabase_id}, imported from https://meta.wikimedia.org/wiki/Translations:Module:CapacityExchange/capacities.json/{qid}-{field}/{lang}",
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
            raise CommandError(f"Metabase API error for {metabase_id}/{lang} {field}: {j}")

    def compose_metawiki_title(self, qid, field, lang):
        base = f"Translations:Module:CapacityExchange/capacities.json/{qid}-{field}"
        return f"{base}/{lang}"

    def set_metawiki_translation(self, session, token, qid, lang, field, value, metabase_id):
        title = self.compose_metawiki_title(qid, field, lang)
        summary = f"CapX sync: set {field} ({lang}) for {qid}"
        if metabase_id:
            summary += f", imported from https://metabase.wikibase.cloud/wiki/Item:{metabase_id}"
        data = {
            "action": "edit",
            "title": title,
            "text": value,
            "summary": summary,
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
        # First, build a mapping of value (QID) -> metabase item id
        map_query = f"""PREFIX wbt:<https://metabase.wikibase.cloud/prop/direct/>
            PREFIX wb: <https://metabase.wikibase.cloud/entity/>
            SELECT DISTINCT ?item ?value WHERE {{
                VALUES ?value {{ {item_ids} }}
                ?item wbt:P5 wb:Q34531.
                ?item wbt:P67/wbt:P1 ?value.
            }}"""
        headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}
        r = requests.get(METABASE_SPARQL_ENDPOINT, params={"query": map_query}, headers=headers, timeout=60)
        r.raise_for_status()
        map_data = r.json()
        value_to_item = {}
        for b in map_data.get("results", {}).get("bindings", []):
            item_uri = b.get("item", {}).get("value")
            value = b.get("value", {}).get("value")
            item_id = self.parse_entity_id(item_uri) if item_uri else None
            if item_id and value:
                value_to_item[value] = item_id
        # store mapping for later resolution
        self.metabase_ids = value_to_item

        # Then fetch label/description terms per language
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

    def get_metabase_id_for_qid(self, metabase_map, qid):
        # Prefer mapping gathered during fetch
        if hasattr(self, "metabase_ids"):
            mid = self.metabase_ids.get(qid)
            if mid:
                return mid
        # Fallback: scan language entries (if any)
        for data in metabase_map.get(qid, {}).values():
            metabase_id = data.get("metabase_id")
            if metabase_id:
                return metabase_id
        return None

    def _normalize_text(self, s):
        if s is None:
            return None
        return str(s).strip()

    def find_mismatches(self, metabase, metawiki):
        mismatches = {}
        qids = set(metabase.keys()) | set(metawiki.keys())
        for qid in sorted(qids):
            langs = set(metabase.get(qid, {}).keys()) | set(metawiki.get(qid, {}).keys())
            for lang in sorted(langs):
                mb = metabase.get(qid, {}).get(lang, {})
                mw = metawiki.get(qid, {}).get(lang, {})
                for field in ("label", "description"):
                    a = self._normalize_text(mb.get(field))
                    b = self._normalize_text(mw.get(field))
                    if self._has_value(a) and self._has_value(b) and a != b:
                        mismatches.setdefault(qid, []).append({
                            "lang": lang,
                            "field": field,
                            "metabase": a,
                            "metawiki": b,
                        })
        return mismatches

    def get_bug_report_user(self):
        user = get_user_model()
        username = "CapacityExchangeBot"
        try:
            return user.objects.get(username=username)
        except user.DoesNotExist:
            try:
                return user.objects.filter(is_superuser=True).order_by("id").first() or user.objects.order_by("id").first()
            except Exception:
                return None

    def bug_title_for_qid(self, qid):
        return f"Translation mismatches for {qid}"

    def ensure_bug_for_mismatches(self, qid, entries, dry_run=False):
        if not entries:
            return None
        title = self.bug_title_for_qid(qid)
        existing = Bug.objects.filter(title=title).first()
        if existing:
            return existing
        # Compose description
        lines = [
            f"Found {len(entries)} translation mismatches for {qid}.",
            "",
        ]
        for e in entries:
            mb = e["metabase"].replace("\n", " ") if e.get("metabase") else ""
            mw = e["metawiki"].replace("\n", " ") if e.get("metawiki") else ""
            if len(mb) > 300:
                mb = mb[:297] + "..."
            if len(mw) > 300:
                mw = mw[:297] + "..."
            lines.append(f"- [{e['lang']}] {e['field']}: metabase=\"{mb}\" | metawiki=\"{mw}\"")
        description = "\n".join(lines)
        # Respect Bug.description max_length (1000)
        max_len = 1000
        if len(description) > max_len:
            note = "\n... (truncated)"
            description = description[: max_len - len(note)] + note

        if dry_run:
            return {
                "title": title,
                "description": description,
            }

        reporter = self.get_bug_report_user()
        if not reporter:
            raise CommandError("Cannot create Bug: no reporter user available.")
        bug = Bug.objects.create(
            user=reporter,
            title=title,
            description=description,
            bug_type="improvement",
        )
        return bug

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
        if getattr(self, "verbosity", 1) >= 2:
            self.stdout.write("Requesting MetaWiki messagecollection index...")
        r = requests.get(METAWIKI_API_ENDPOINT, params=index_params, timeout=30, headers=headers)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("messagecollection", [])
        translations_by_qid: dict[str, dict[str, dict[str, str]]] = {}
        total_pages = len(pages)
        for idx, page in enumerate(pages, 1):
            title = page.get("title", "")
            title_params = {
                "action": "query",
                "format": "json",
                "meta": "messagetranslations",
                "formatversion": "2",
                "mttitle": title
            }
            if getattr(self, "verbosity", 1) >= 2:
                self.stdout.write(f"Requesting translations for: {title} (message {idx} of {total_pages})")
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
