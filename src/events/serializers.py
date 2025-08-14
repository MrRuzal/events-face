from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source="venue.name", read_only=True)

    class Meta:
        model = Event
        fields = ["id", "name", "event_time", "status", "venue", "venue_name"]
