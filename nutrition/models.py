from django.db import models
from residents.models import Resident


class NutritionAssessment(models.Model):

    STATUS_CHOICES = [
        ('Underweight', 'Underweight'),
        ('Normal', 'Normal'),
        ('Overweight', 'Overweight'),
        ('Obese', 'Obese'),
    ]

    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name='assessments'
    )

    assessment_date = models.DateField()

    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Height in centimeters"
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Weight in kilograms"
    )

    bmi = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        editable=False
    )

    nutritional_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        editable=False
    )

    remarks = models.TextField(
    editable=False,
    blank=True,
    default=""
)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        height_m = float(self.height) / 100

        bmi = float(self.weight) / (height_m * height_m)

        self.bmi = round(bmi, 2)

        if bmi < 18.5:
            self.nutritional_status = "Underweight"
            self.remarks = (
                "Needs nutritional intervention and regular monitoring."
            )

        elif bmi < 25:
            self.nutritional_status = "Normal"
            self.remarks = (
                "Normal nutritional status. Continue a balanced diet and healthy lifestyle."
            )

        elif bmi < 30:
            self.nutritional_status = "Overweight"
            self.remarks = (
                "Advise healthy eating habits, regular exercise, and continuous monitoring."
            )

        else:
            self.nutritional_status = "Obese"
            self.remarks = (
                "Requires weight management, dietary counseling, and regular follow-up."
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.resident} - {self.assessment_date}"