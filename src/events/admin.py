from django.contrib import admin
from .models import Venue, Event


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "event_time", "status", "venue")
    list_filter = ("status", "event_time")
    search_fields = ("name",)
