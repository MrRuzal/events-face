from django.db import models


class SyncResult(models.Model):
    sync_date = models.DateField(auto_now_add=True)
    new_events_count = models.PositiveIntegerField(default=0)
    updated_events_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Sync {self.sync_date} - New: {self.new_events_count}, Updated: {self.updated_events_count}"
