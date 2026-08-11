from django.contrib import admin

from .models import (
    NutritionAssessment,
    NutritionRule,
    FollowUpRecord,
)


@admin.register(NutritionRule)
class NutritionRuleAdmin(admin.ModelAdmin):

    list_display = (
        'status_name',
        'bmi_min',
        'bmi_max',
        'monitoring_flag',
        'is_active',
        'approved_by',
    )

    list_filter = (
        'status_name',
        'monitoring_flag',
        'is_active',
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change
    ):

        if obj.approved_by_id is None:
            obj.approved_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change
        )


@admin.register(NutritionAssessment)
class NutritionAssessmentAdmin(admin.ModelAdmin):

    list_display = (
        'resident',
        'assessment_date',
        'height',
        'weight',
        'bmi',
        'nutritional_status',
        'monitoring_flag',
        'assessed_by',
    )

    list_filter = (
        'nutritional_status',
        'monitoring_flag',
        'assessment_date',
    )

    search_fields = (
        'resident__first_name',
        'resident__last_name',
        'resident__resident_id',
    )


@admin.register(FollowUpRecord)
class FollowUpRecordAdmin(admin.ModelAdmin):

    list_display = (
        'assessment',
        'follow_up_date',
        'status',
        'recorded_by',
        'next_follow_up_date',
    )

    list_filter = (
        'status',
        'follow_up_date',
    )