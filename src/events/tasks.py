from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import Event


@shared_task
def cleanup_old_events():
    cutoff = timezone.now() - timezone.timedelta(
        days=settings.EVENT_CLEANUP_DAYS
    )
    old_events = Event.objects.filter(event_time__lt=cutoff)
    deleted_count, _ = old_events.delete()
    return deleted_count
