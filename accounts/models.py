from django.db import models


class SystemSettings(models.Model):
    barangay_name = models.CharField(
        max_length=120,
        default='Barangay Can-Uguib',
    )
    health_center_name = models.CharField(
        max_length=160,
        blank=True,
    )
    contact_number = models.CharField(
        max_length=32,
        blank=True,
    )
    contact_email = models.EmailField(
        blank=True,
    )
    address = models.CharField(
        max_length=255,
        blank=True,
    )

    def __str__(self):
        return self.barangay_name
