from django.contrib import admin
from django.urls import include, path

from events.views import EventListView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("authapp.urls")),
    path("api/events/", EventListView.as_view(), name="event-list"),
]
