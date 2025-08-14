import time
from datetime import datetime, timedelta

import requests
from django.core.management.base import BaseCommand

from events.models import Event, Venue
from sync.models import SyncResult


class Command(BaseCommand):
    help = "Synchronize events from events-provider"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date", type=str, help="Date for sync in YYYY-MM-DD format"
        )
        parser.add_argument(
            "--all", action="store_true", help="Sync all events"
        )

    def handle(self, *args, **options):
        date_str = options.get("date")
        all_flag = options.get("all", False)

        if all_flag:
            url = "https://events.k3scluster.tech/api/events/"
        else:
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    self.stderr.write(self.style.ERROR("Invalid date format"))
                    return
            else:
                date_obj = datetime.now().date() - timedelta(days=1)

            url = f"https://events.k3scluster.tech/api/events/?changed_at={date_obj}"

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(url)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Attempt {attempt} failed: {e}. Retrying..."
                        )
                    )
                    time.sleep(2)
                else:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Failed to fetch events after {max_retries} attempts: {e}"
                        )
                    )
                    return

        events_data = response.json()
        new_count = 0
        updated_count = 0

        for ev in events_data:
            venue_data = ev.get("venue")
            venue = None
            if venue_data:
                venue, _ = Venue.objects.get_or_create(
                    id=venue_data.get("id"),
                    defaults={"name": venue_data.get("name", "")},
                )

            event_obj, created = Event.objects.update_or_create(
                id=ev["id"],
                defaults={
                    "name": ev.get("name"),
                    "event_time": ev.get("event_time"),
                    "status": ev.get("status", "open"),
                    "venue": venue,
                },
            )
            if created:
                new_count += 1
            else:
                updated_count += 1

        SyncResult.objects.create(
            new_events_count=new_count, updated_events_count=updated_count
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync finished. New: {new_count}, Updated: {updated_count}"
            )
        )
