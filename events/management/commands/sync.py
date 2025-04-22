from django.core.management.base import BaseCommand
from events.models import Events
import requests

class Command(BaseCommand):
    help = 'Sync WikiLearn events with CapX events'

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        wikilearn_events = Events.objects.filter(url__contains='https://learn.wiki/courses/')
        for event in wikilearn_events:
            api_url = f"https://learn.wiki/api/courses/v1/courses/{event.url.split('/')[4]}"
            response = requests.get(api_url)
            if response.status_code != 200:
                raise ConnectionError("Wikilearn service is not available.")

            data = response.json()
            
            if not data.get("id"):
                raise ValueError("Invalid Wikilearn ID.")

            event.name = data.get("name") if data.get("name") != event.name else event.name
            event.time_begin = data.get("start") if data.get("start") != event.time_begin else event.time_begin
            event.time_end = data.get("end") if data.get("end") != event.time_end else event.time_end
            event.image_url = data.get("media").get("image").get("raw") if data.get("media").get("image").get("raw") != event.image_url else event.image_url
            event.save()
            
            if self.verbosity >= 2:
                self.stdout.write(f"Successfully synced event {event.name}")