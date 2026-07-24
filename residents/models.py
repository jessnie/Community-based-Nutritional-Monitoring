from django.db import models
from datetime import date


class Resident(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    resident_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)

    sex = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    birth_date = models.DateField()

    address = models.TextField()

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def age(self):
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - (
                (today.month, today.day)
                < (self.birth_date.month, self.birth_date.day)
            )
        )

    def __str__(self):
        return f"{self.resident_id} - {self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']