import uuid
import enum
from django.db import models


class StatusEnum(enum.StrEnum):  
    OPEN = "open"
    CLOSED = "closed"


class Venue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    event_time = models.DateTimeField()
    status = models.CharField(
        max_length=6,
        choices=[(status.value, status.name.title()) for status in StatusEnum],
    )
    venue = models.ForeignKey(
        Venue,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )

    def __str__(self):
        return self.name
