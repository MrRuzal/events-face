from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Event
from .serializers import EventSerializer


class EventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["name"]
    ordering_fields = ["event_time"]
    ordering = ["event_time"]

    def get_queryset(self):
        return Event.objects.filter(status="open").select_related("venue")
