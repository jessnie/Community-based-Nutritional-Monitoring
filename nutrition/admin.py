from django.contrib import admin
from .models import NutritionAssessment


@admin.register(NutritionAssessment)
class NutritionAssessmentAdmin(admin.ModelAdmin):

    list_display = (
        'resident',
        'assessment_date',
        'height',
        'weight',
        'bmi',
        'nutritional_status',
    )

    list_filter = (
        'nutritional_status',
        'assessment_date',
    )

    search_fields = (
        'resident__first_name',
        'resident__last_name',
        'resident__resident_id',
    )