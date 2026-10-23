import requests
from django.core.management.base import BaseCommand, CommandError

from CapX.useragent import get_user_agent

USER_AGENT = get_user_agent("SyncCampaigns")

METABASE_SPARQL_ENDPOINT = "https://metabase.wikibase.cloud/query/sparql"


class Command(BaseCommand):
    help = (
        "Fetch campaigns from Metabase (Wikibase). "
        "Queries for items matching: ?item wbt:P5/wbt:P4* wb:Q22217"
    )

    def handle(self, *args, **options):
        self.stdout.write("Fetching campaigns from Metabase...")
        campaigns_data = self.fetch_metabase_campaigns()

        if not campaigns_data:
            self.stdout.write("No campaigns found in Metabase.")
            return

        self.stdout.write(f"Found {len(campaigns_data)} campaigns in Metabase.")

        for campaign in campaigns_data:
            self.stdout.write(
                f"  {campaign['qid']}: {campaign['name'] or '(no label)'} "
                f"[wikidata: {campaign['wikidata_qid'] or '(none)'}]"
            )

    def fetch_metabase_campaigns(self):
        """
        Fetch campaigns from Metabase using SPARQL query:
        ?item wbt:P5/wbt:P4* wb:Q22217

        This finds all items that are instances of (P5) a class that is a subclass of (P4*)
        Q22217 (campaign type).
        """
        # SPARQL query to find all campaign items
        # P5 = instance of
        # P4 = subclass of
        # Q22217 = campaign type
        query = """
        PREFIX wbt: <https://metabase.wikibase.cloud/prop/direct/>
        PREFIX wb: <https://metabase.wikibase.cloud/entity/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>

        SELECT ?item ?itemLabel ?itemDescription ?startDate ?endDate ?image ?wikidataQid ?qid WHERE {
            ?item wbt:P5/wbt:P4* wb:Q22217.
            BIND(STRAFTER(STR(?item), STR(wb:)) AS ?qid)
            OPTIONAL { ?item rdfs:label ?itemLabel. FILTER(LANG(?itemLabel) = "en") }
            OPTIONAL { ?item schema:description ?itemDescription. FILTER(LANG(?itemDescription) = "en") }
            OPTIONAL { ?item wbt:P8 ?startDate. }  # start date property
            OPTIONAL { ?item wbt:P9 ?endDate. }     # end date property
            OPTIONAL { ?item wbt:P10 ?image. }      # image property
            OPTIONAL { ?item wbt:P1 ?wikidataQid. } # Wikidata QID property
        }
        ORDER BY ?itemLabel
        """

        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": USER_AGENT,
        }

        try:
            response = requests.get(
                METABASE_SPARQL_ENDPOINT,
                params={"query": query},
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

            name = binding.get("itemLabel", {}).get("value", "")
            description = binding.get("itemDescription", {}).get("value", "")
            start_date = binding.get("startDate", {}).get("value")
            end_date = binding.get("endDate", {}).get("value")
            image = binding.get("image", {}).get("value")
            wikidata_qid = binding.get("wikidataQid", {}).get("value")

            campaigns.append(
                {
                    "qid": qid,
                    "name": name,
                    "description": description,
                    "start_date": start_date,
                    "end_date": end_date,
                    "image_url": image,
                    "wikidata_qid": wikidata_qid,
                }
            )

        return campaigns
