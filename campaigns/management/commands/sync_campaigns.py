from datetime import datetime

import requests
from django.core.management.base import BaseCommand, CommandError

from campaigns.models import Campaign
from skills.models import Skill
from CapX.useragent import get_user_agent

METABASE_SPARQL_ENDPOINT = "https://metabase.wikibase.cloud/query/sparql"

QUERY = """
PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
PREFIX wb: <https://metabase.wikibase.cloud/entity/>

SELECT ?qid
       (MIN(?startDate) AS ?minStartDate)
       (MAX(?endDate) AS ?maxEndDate)
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?org), STR(wb:)); SEPARATOR="|") AS ?orgQids)
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?location), STR(wb:)); SEPARATOR="|") AS ?locationQids)
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?language), STR(wb:)); SEPARATOR="|") AS ?languageQids)
       (GROUP_CONCAT(DISTINCT ?skillWikidataQid; SEPARATOR="|") AS ?skillWikidataQids)
WHERE {
    # campaign items
    ?item wbt:P5/wbt:P4* wb:Q22217.
    BIND(STRAFTER(STR(?item), STR(wb:)) AS ?qid)
    # date
    OPTIONAL { ?item wbt:P6 ?startDate. }
    OPTIONAL { ?item wbt:P7 ?endDate. }
    OPTIONAL { ?item wbt:P23 ?pointInTime. }
    BIND(COALESCE(?startDate, ?pointInTime) AS ?startDate)
    BIND(COALESCE(?endDate, ?pointInTime) AS ?endDate)
    # info
    OPTIONAL { ?item wbt:P14 ?org. }
    OPTIONAL { ?item wbt:P27 ?location. }
    OPTIONAL { ?item wbt:P52 ?language. }
    OPTIONAL {
      # keywords of this campaign mapping to CapX skills
      ?item wbt:P15/wbt:P1 ?skillWikidataQid.
      ?skill wbt:P5 wb:Q34531;
             wbt:P67/wbt:P1 ?skillWikidataQid.
    }
    OPTIONAL {
      # keywords of the group mapping to CapX skills
      ?item wbt:P35/wbt:P15/wbt:P1 ?skillWikidataQid.
      ?skill wbt:P5 wb:Q34531;
             wbt:P67/wbt:P1 ?skillWikidataQid.
    }
    # exclude campaign groups (items that have sub-campaigns)
    MINUS {
        ?item wbt:P35/wbt:P5 wb:Q22217.
    }
}
GROUP BY ?qid
ORDER BY ?qid
"""


class Command(BaseCommand):
    help = (
        "Fetch campaigns from Metabase (Wikibase) and sync to database. "
        "Queries for items matching: ?item wbt:P5/wbt:P4* wb:Q22217"
    )

    def handle(self, *args, **options):
        self.stdout.write("Fetching campaigns from Metabase...")
        campaigns_data = self.fetch_metabase_campaigns()

        if not campaigns_data:
            self.stdout.write("No campaigns found in Metabase.")
            return

        self.stdout.write(f"Found {len(campaigns_data)} campaigns in Metabase.")

        created_count = 0
        updated_count = 0
        unchanged_count = 0

        for campaign_data in campaigns_data:
            qid = campaign_data["qid"]
            skill_wikidata_qids = campaign_data["skillWikidataQids"]

            defaults = {
                "min_start_date": campaign_data["min_start_date"],
                "max_end_date": campaign_data["max_end_date"],
                "org_qids": campaign_data["orgQids"],
                "location_qids": campaign_data["locationQids"],
                "language_qids": campaign_data["languageQids"],
                "skill_wikidata_qids": skill_wikidata_qids,
            }

            campaign, created = Campaign.objects.get_or_create(
                metabase_qid=qid,
                defaults=defaults,
            )

            # Sync skills based on skill_wikidata_qids using model method
            skill_qids = [qid.strip() for qid in skill_wikidata_qids.split("|") if qid.strip()]
            synced_skill_ids = campaign.sync_skills(skill_wikidata_qids)

            # Verify all expected skills were synced
            if skill_qids:
                missing = set(skill_qids) - set(
                    Skill.objects.filter(id__in=synced_skill_ids).values_list("skill_wikidata_item", flat=True)
                )
                if missing:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Campaign {campaign.metabase_qid}: {len(missing)} skill(s) not found in database: {sorted(missing)}"
                        )
                    )

            if created:
                created_count += 1
                self.stdout.write(f"Created: {campaign.metabase_qid}")
            else:
                changed = False
                for field, new_value in defaults.items():
                    current_value = getattr(campaign, field)
                    if current_value != new_value:
                        setattr(campaign, field, new_value)
                        changed = True
                if changed:
                    campaign.save()
                    updated_count += 1
                    self.stdout.write(f"Updated: {campaign.metabase_qid}")
                else:
                    unchanged_count += 1
                    self.stdout.write(f"No changes: {campaign.metabase_qid}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. Created: {created_count}, Updated: {updated_count}, No changes: {unchanged_count}"
            )
        )

    def fetch_metabase_campaigns(self):
        """
        Fetch campaigns from Metabase using SPARQL query.
        """
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": get_user_agent("SyncCampaigns"),
        }

        try:
            response = requests.get(
                METABASE_SPARQL_ENDPOINT,
                params={"query": QUERY},
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise CommandError(f"Failed to query Metabase SPARQL endpoint: {e}")

        campaigns = []
        for binding in data.get("results", {}).get("bindings", []):
            qid = binding.get("qid", {}).get("value", "")

            if not qid:
                continue

            min_start_date = binding.get("minStartDate", {}).get("value", "")
            max_end_date = binding.get("maxEndDate", {}).get("value", "")
            org_qids = binding.get("orgQids", {}).get("value", "")
            location_qids = binding.get("locationQids", {}).get("value", "")
            language_qids = binding.get("languageQids", {}).get("value", "")
            skill_wikidata_qids = binding.get("skillWikidataQids", {}).get("value", "")

            try:
                if min_start_date:
                    min_start_date = datetime.fromisoformat(min_start_date).date()
                else:
                    min_start_date = None
                if max_end_date:
                    max_end_date = datetime.fromisoformat(max_end_date).date()
                else:
                    max_end_date = None
            except ValueError:
                print(f"failed to parse dates: {qid}")
                continue

            campaigns.append(
                {
                    "qid": qid,
                    "min_start_date": min_start_date,
                    "max_end_date": max_end_date,
                    "orgQids": org_qids,
                    "locationQids": location_qids,
                    "languageQids": language_qids,
                    "skillWikidataQids": skill_wikidata_qids,
                }
            )

        return campaigns
