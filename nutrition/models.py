from django.conf import settings
from django.db import models
from django.utils import timezone

from residents.models import Resident

class NutritionRule(models.Model):

    STATUS_CHOICES = [
        ('Underweight', 'Underweight'),
        ('Normal', 'Normal'),
        ('Overweight', 'Overweight'),
        ('Obese', 'Obese'),
    ]

    MONITORING_FLAG_CHOICES = [
        ('Routine Monitoring', 'Routine Monitoring'),
        ('Needs Follow-up', 'Needs Follow-up'),
    ]

    status_name = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        unique=True
    )

    bmi_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    bmi_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    monitoring_flag = models.CharField(
        max_length=30,
        choices=MONITORING_FLAG_CHOICES
    )

    is_active = models.BooleanField(
        default=True
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_nutrition_rules'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.status_name
    
class NutritionAssessment(models.Model):

    STATUS_CHOICES = [
        ('Underweight', 'Underweight'),
        ('Normal', 'Normal'),
        ('Overweight', 'Overweight'),
        ('Obese', 'Obese'),
    ]
    MONITORING_FLAG_CHOICES = [
    ('Routine Monitoring', 'Routine Monitoring'),
    ('Needs Follow-up', 'Needs Follow-up'),
    ]

    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name='assessments'
    )

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nutrition_assessments'
    )

    rule = models.ForeignKey(
    NutritionRule,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
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

    monitoring_flag = models.CharField(
    max_length=30,
    choices=MONITORING_FLAG_CHOICES,
    editable=False,
    default='Routine Monitoring'
    )

    remarks = models.TextField(
        editable=False,
        blank=True,
        default=""
    )

    intervention = models.TextField(
        editable=False,
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):

        # -------------------------
        # Compute BMI
        # -------------------------

        height_m = float(self.height) / 100

        bmi = float(self.weight) / (height_m * height_m)

        self.bmi = round(bmi, 2)

        # -------------------------
        # Determine Nutritional Status
        # -------------------------

        if bmi < 18.5:
            self.nutritional_status = "Underweight"

        elif bmi < 25:
            self.nutritional_status = "Normal"

        elif bmi < 30:
            self.nutritional_status = "Overweight"

        else:
            self.nutritional_status = "Obese"

        # -------------------------
        # Determine Age Category
        # -------------------------

        age_group = self.resident.age_category

        # -------------------------
        # Generate Remarks & Intervention
        # -------------------------

        if age_group == "Under Five":

            if self.nutritional_status == "Underweight":

                self.remarks = (
                    "Growth is below the expected nutritional level for the child's age."
                )

                self.intervention = (
                    "• Monthly growth monitoring\n"
                    "• Breastfeeding/feeding counseling\n"
                    "• Micronutrient supplementation if needed\n"
                    "• Refer to the Barangay Nutrition Scholar (BNS)\n"
                    "• Encourage nutritious complementary feeding"
                )

            elif self.nutritional_status == "Normal":

                self.remarks = (
                    "Child has a healthy nutritional status."
                )

                self.intervention = (
                    "• Continue exclusive/balanced feeding\n"
                    "• Monthly growth monitoring\n"
                    "• Maintain complete immunization\n"
                    "• Encourage healthy eating habits"
                )

            elif self.nutritional_status == "Overweight":

                self.remarks = (
                    "Child is above the recommended weight."
                )

                self.intervention = (
                    "• Limit sugary foods and drinks\n"
                    "• Encourage active play\n"
                    "• Educate parents on healthy feeding practices\n"
                    "• Monitor growth regularly"
                )

            else:

                self.remarks = (
                    "Child is obese and requires immediate nutrition management."
                )

                self.intervention = (
                    "• Refer to physician/nutritionist\n"
                    "• Family nutrition counseling\n"
                    "• Healthy diet planning\n"
                    "• Regular weight monitoring"
                )

        elif age_group == "Child":

            if self.nutritional_status == "Underweight":

                self.remarks = (
                    "Child is underweight."
                )

                self.intervention = (
                    "• Balanced nutritious meals\n"
                    "• Deworming if necessary\n"
                    "• Nutrition education for parents\n"
                    "• Monthly BMI monitoring"
                )

            elif self.nutritional_status == "Normal":

                self.remarks = (
                    "Child has a normal nutritional status."
                )

                self.intervention = (
                    "• Continue healthy eating\n"
                    "• Encourage physical activities\n"
                    "• Routine nutrition monitoring"
                )

            elif self.nutritional_status == "Overweight":

                self.remarks = (
                    "Child is overweight."
                )

                self.intervention = (
                    "• Reduce junk foods\n"
                    "• Increase outdoor activities\n"
                    "• Nutrition counseling\n"
                    "• Regular BMI monitoring"
                )

            else:

                self.remarks = (
                    "Child is obese."
                )

                self.intervention = (
                    "• Nutrition counseling\n"
                    "• Increase physical activity\n"
                    "• Reduce sugary drinks\n"
                    "• Refer when necessary"
                )

        elif age_group == "Adolescent":

            if self.nutritional_status == "Underweight":

                self.remarks = (
                    "Adolescent has inadequate nutritional status."
                )

                self.intervention = (
                    "• Increase protein intake\n"
                    "• Healthy meal planning\n"
                    "• Nutrition education\n"
                    "• Monthly assessment"
                )

            elif self.nutritional_status == "Normal":

                self.remarks = (
                    "Adolescent has a healthy nutritional status."
                )

                self.intervention = (
                    "• Maintain balanced diet\n"
                    "• Regular exercise\n"
                    "• Annual nutrition assessment"
                )

            elif self.nutritional_status == "Overweight":

                self.remarks = (
                    "Adolescent is overweight."
                )

                self.intervention = (
                    "• Healthy diet\n"
                    "• Daily physical activity\n"
                    "• Reduce sugary snacks\n"
                    "• Weight monitoring"
                )

            else:

                self.remarks = (
                    "Adolescent is obese."
                )

                self.intervention = (
                    "• Physician referral if needed\n"
                    "• Nutrition counseling\n"
                    "• Exercise program\n"
                    "• Lifestyle modification"
                )

        elif age_group == "Adult":

            if self.nutritional_status == "Underweight":

                self.remarks = (
                    "Adult is underweight."
                )

                self.intervention = (
                    "• High-calorie, high-protein diet\n"
                    "• Nutrition counseling\n"
                    "• Monthly monitoring\n"
                    "• Assess underlying illnesses"
                )

            elif self.nutritional_status == "Normal":

                self.remarks = (
                    "Adult has normal nutritional status."
                )

                self.intervention = (
                    "• Maintain balanced diet\n"
                    "• Continue regular exercise\n"
                    "• Annual BMI assessment"
                )

            elif self.nutritional_status == "Overweight":

                self.remarks = (
                    "Adult is overweight."
                )

                self.intervention = (
                    "• Reduce calorie intake\n"
                    "• Increase physical activity\n"
                    "• Monthly BMI monitoring"
                )

            else:

                self.remarks = (
                    "Adult is obese."
                )

                self.intervention = (
                    "• Weight management program\n"
                    "• Nutrition counseling\n"
                    "• Exercise plan\n"
                    "• Monitor blood pressure and blood sugar"
                )

        else:  # Senior Citizen

            if self.nutritional_status == "Underweight":

                self.remarks = (
                    "Senior citizen is at risk of malnutrition."
                )

                self.intervention = (
                    "• Protein-rich meals\n"
                    "• Hydration monitoring\n"
                    "• Caregiver nutrition education\n"
                    "• Monthly weight monitoring"
                )

            elif self.nutritional_status == "Normal":

                self.remarks = (
                    "Senior citizen has a healthy nutritional status."
                )

                self.intervention = (
                    "• Continue balanced diet\n"
                    "• Light physical activity\n"
                    "• Regular nutrition assessment"
                )

            elif self.nutritional_status == "Overweight":

                self.remarks = (
                    "Senior citizen is overweight."
                )

                self.intervention = (
                    "• Reduce saturated fats\n"
                    "• Encourage walking\n"
                    "• Monitor chronic diseases"
                )

            else:

                self.remarks = (
                    "Senior citizen is obese."
                )

                self.intervention = (
                    "• Physician referral\n"
                    "• Nutrition counseling\n"
                    "• Weight management\n"
                    "• Regular health monitoring"
                )
        # -------------------------
        # Monitoring Flag & Rule
        # -------------------------

        matching_rule = NutritionRule.objects.filter(
            status_name=self.nutritional_status,
            is_active=True
        ).first()

        if matching_rule:
            self.rule = matching_rule
            self.monitoring_flag = matching_rule.monitoring_flag

        else:
            self.rule = None

            if self.nutritional_status == "Normal":
                self.monitoring_flag = "Routine Monitoring"
            else:
                self.monitoring_flag = "Needs Follow-up"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.resident} - {self.assessment_date}"


class FollowUpRecord(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('For Referral', 'For Referral'),
    ]

    assessment = models.ForeignKey(
        NutritionAssessment,
        on_delete=models.CASCADE,
        related_name='follow_ups'
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='follow_up_records'
    )

    follow_up_date = models.DateField(
        default=timezone.localdate
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    notes = models.TextField(
        blank=True,
        default=''
    )

    next_follow_up_date = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            '-follow_up_date',
            '-created_at'
        ]

    def __str__(self):
        return (
            f"{self.assessment.resident} - "
            f"{self.follow_up_date}"
        )