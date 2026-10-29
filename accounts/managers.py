from django.db import models


class ActiveRecordManager(models.Manager):
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(archived_at__isnull=True)
