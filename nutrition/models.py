from django.conf import settings
from django.db import models
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from functools import lru_cache
import json
import math
from pathlib import Path

from accounts.managers import ActiveRecordManager
from residents.models import Resident


class ActiveAssessmentManager(ActiveRecordManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            resident__archived_at__isnull=True
        )


class ActiveFollowUpManager(ActiveRecordManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            assessment__archived_at__isnull=True,
            assessment__resident__archived_at__isnull=True,
        )


@lru_cache(maxsize=1)
def _who_bmi_reference():
    reference_path = Path(__file__).parent / 'data' / 'who_bmi_lms.json'
    return json.loads(reference_path.read_text(encoding='utf-8'))


def classify_nutritional_status(bmi, sex, age_months):
    """Classify with WHO BMI-for-age references through 19 years.

    References: WHO Child Growth Standards (0-5 years) and WHO Growth
    Reference (5-19 years), BMI-for-age indicators.
    """
    if age_months > 228:
        if bmi < 18.5:
            return 'Underweight'
        if bmi < 25:
            return 'Normal'
        if bmi < 30:
            return 'Overweight'
        return 'Obese'

    sex_key = {'Female': 'girls', 'Male': 'boys'}.get(sex)
    if sex_key is None or age_months < 0:
        raise ValueError('A valid sex and age are required for BMI classification.')

    l_value, median, variation = _who_bmi_reference()[sex_key][str(age_months)]
    if l_value == 0:
        z_score = math.log(bmi / median) / variation
    else:
        z_score = ((bmi / median) ** l_value - 1) / (l_value * variation)

    if z_score < -2:
        return 'Underweight'
    if age_months <= 60:
        if z_score > 3:
            return 'Obese'
        if z_score > 2:
            return 'Overweight'
    else:
        if z_score > 2:
            return 'Obese'
        if z_score > 1:
            return 'Overweight'
    return 'Normal'


def _age_at(birth_date, assessment_date):
    age = assessment_date.year - birth_date.year
    if (assessment_date.month, assessment_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _age_months_at(birth_date, assessment_date):
    months = (assessment_date.year - birth_date.year) * 12
    months += assessment_date.month - birth_date.month
    if assessment_date.day < birth_date.day:
        months -= 1
    return months


def _age_group_at(birth_date, assessment_date):
    age = _age_at(birth_date, assessment_date)
    if age <= 5:
        return 'Under Five'
    if age <= 12:
        return 'Child'
    if age <= 17:
        return 'Adolescent'
    if age <= 59:
        return 'Adult'
    return 'Senior Citizen'

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

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = ActiveAssessmentManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = 'all_objects'
        default_manager_name = 'objects'


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

        age_months = _age_months_at(
            self.resident.birth_date,
            self.assessment_date
        )
        self.nutritional_status = classify_nutritional_status(
            bmi,
            self.resident.sex,
            age_months
        )

        # -------------------------
        # Determine Age Category
        # -------------------------

        age_group = _age_group_at(
            self.resident.birth_date,
            self.assessment_date
        )

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
        else:
            self.rule = None

        self.monitoring_flag = (
            'Routine Monitoring'
            if self.nutritional_status == 'Normal'
            else 'Needs Follow-up'
        )

        super().save(*args, **kwargs)

        latest_assessment = current_assessments().get(
            resident=self.resident
        )
        if latest_assessment.pk != self.pk:
            return

        active_followups = FollowUpRecord.objects.filter(
            assessment__resident=self.resident,
            status__in=['Pending', 'For Referral']
        )
        if self.nutritional_status == 'Normal':
            for followup in active_followups:
                followup.status = 'Completed'
                resolution_note = (
                    f'Monitoring resolved by normal assessment on '
                    f'{self.assessment_date:%Y-%m-%d}.'
                )
                followup.notes = '\n'.join(
                    part for part in (followup.notes, resolution_note) if part
                )
                followup.save(update_fields=['status', 'notes', 'updated_at'])
        else:
            pending_followups = active_followups.filter(
                status='Pending'
            ).exclude(assessment=self)
            for followup in pending_followups:
                followup.status = 'Completed'
                continuation_note = (
                    f'Monitoring remains active; newer assessment recorded on '
                    f'{self.assessment_date:%Y-%m-%d}.'
                )
                followup.notes = '\n'.join(
                    part for part in (followup.notes, continuation_note) if part
                )
                followup.save(update_fields=['status', 'notes', 'updated_at'])

            if not active_followups.filter(assessment=self).exists():
                FollowUpRecord.objects.create(
                    assessment=self,
                    follow_up_date=self.assessment_date,
                    status='Pending',
                    notes='Monitoring remains active until a normal assessment is recorded.',
                )

    def __str__(self):
        return f"{self.resident} - {self.assessment_date}"


def current_assessments():
    latest_for_resident = NutritionAssessment.objects.filter(
        resident_id=OuterRef('resident_id')
    ).order_by(
        '-assessment_date',
        '-created_at',
        '-pk'
    ).values('pk')[:1]

    return NutritionAssessment.objects.filter(
        pk=Subquery(latest_for_resident)
    )


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

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = ActiveFollowUpManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = 'all_objects'
        default_manager_name = 'objects'

        ordering = [
            '-follow_up_date',
            '-created_at'
        ]

    def __str__(self):
        return (
            f"{self.assessment.resident} - "
            f"{self.follow_up_date}"
        )

    def save(self, *args, **kwargs):
        if self.status == 'Completed' and self.assessment_id:
            latest_assessment = current_assessments().filter(
                resident_id=self.assessment.resident_id
            ).first()
            if latest_assessment and latest_assessment.nutritional_status != 'Normal':
                self.status = 'Pending'
                completion_note = (
                    'Monitoring remains active until a Normal assessment is recorded.'
                )
                if completion_note not in self.notes:
                    self.notes = '\n'.join(
                        part for part in (self.notes, completion_note) if part
                    )
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {
                        'status',
                        'notes',
                    }

        super().save(*args, **kwargs)