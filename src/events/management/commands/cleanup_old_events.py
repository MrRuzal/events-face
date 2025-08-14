from django.core.management.base import BaseCommand
from django.utils import timezone
from events.models import Event


class Command(BaseCommand):
    help = "Delete events that ended more than 7 days ago"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(days=7)
        old_events = Event.objects.filter(event_time__lt=cutoff)
        count = old_events.count()
        old_events.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} old events"))
