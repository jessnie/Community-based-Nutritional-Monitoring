from django.conf import settings
from django.db import models
from datetime import date

from accounts.managers import ActiveRecordManager


class Resident(models.Model):

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    resident_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    first_name = models.CharField(max_length=100)

    middle_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    last_name = models.CharField(max_length=100)

    sex = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    birth_date = models.DateField()

    # Zone
    address = models.CharField(
        max_length=100
    )

    contact_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    guardian_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='created_residents')

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = ActiveRecordManager()
    all_objects = models.Manager()

    @property
    def age(self):

        today = date.today()

        return (
            today.year
            - self.birth_date.year
            - (
                (today.month, today.day)
                <
                (self.birth_date.month, self.birth_date.day)
            )
        )

    @property
    def age_category(self):
        """
        Automatically determines the resident's age category.
        """

        if self.age <= 5:
            return "Under Five"

        elif self.age <= 12:
            return "Child"

        elif self.age <= 17:
            return "Adolescent"

        elif self.age <= 59:
            return "Adult"

        else:
            return "Senior Citizen"

    def save(self, *args, **kwargs):

        if not self.resident_id:

            last_resident = (
                Resident.all_objects
                .order_by('-id')
                .first()
            )

            if last_resident:

                try:

                    last_number = int(
                        last_resident.resident_id.split('-')[1]
                    )

                except (IndexError, ValueError):

                    last_number = last_resident.id

                new_number = last_number + 1

            else:

                new_number = 1

            self.resident_id = f"RES-{new_number:06d}"

        super().save(*args, **kwargs)

    def __str__(self):

        return (
            f"{self.resident_id} - "
            f"{self.first_name} {self.last_name}"
        )

    class Meta:
        base_manager_name = 'all_objects'
        default_manager_name = 'objects'

        ordering = [
            'last_name',
            'first_name'
        ]