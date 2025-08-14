from django.urls import path, include
from django.contrib import admin
from events.views import EventListView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("authapp.urls")),
    path("api/events/", EventListView.as_view(), name="event-list"),
]
