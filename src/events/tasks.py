from celery import shared_task
from django.utils import timezone
from .models import Event


@shared_task
def cleanup_old_events():
    cutoff = timezone.now() - timezone.timedelta(days=7)
    old_events = Event.objects.filter(event_time__lt=cutoff)
    count = old_events.count()
    old_events.delete()
    return f"Deleted {count} old events"
