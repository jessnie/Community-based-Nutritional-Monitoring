from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth

from nutrition.models import NutritionAssessment, FollowUpRecord
from residents.models import Resident


def get_template(request, staff_template, admin_template):
    if request.user.is_superuser:
        return admin_template

    return staff_template


@login_required(login_url='login')
def analytics_dashboard(request):

    # ==========================================
    # BASE QUERYSETS
    # ==========================================

    assessments = NutritionAssessment.objects.all()
    residents = Resident.objects.all()
    followups = FollowUpRecord.objects.all()


    # ==========================================
    # BASIC COUNTS
    # ==========================================

    total_residents = residents.count()
    total_assessments = assessments.count()
    total_followups = followups.count()


    # ==========================================
    # UNIQUE RESIDENTS ASSESSED
    # ==========================================

    assessed_residents = (
        assessments
        .values('resident_id')
        .distinct()
        .count()
    )

    coverage = 0

    if total_residents > 0:
        coverage = round(
            (assessed_residents / total_residents) * 100,
            1
        )


    # ==========================================
    # NUTRITION STATUS
    # ==========================================

    normal = assessments.filter(
        nutritional_status='Normal'
    ).count()

    underweight = assessments.filter(
        nutritional_status='Underweight'
    ).count()

    overweight = assessments.filter(
        nutritional_status='Overweight'
    ).count()

    obese = assessments.filter(
        nutritional_status='Obese'
    ).count()


    # ==========================================
    # MONITORING FLAGS
    # ==========================================

    routine_monitoring = assessments.filter(
        monitoring_flag='Routine Monitoring'
    ).count()

    needs_followup = assessments.filter(
        monitoring_flag='Needs Follow-up'
    ).count()


    # ==========================================
    # FOLLOW-UP STATUS
    # ==========================================

    pending_followups = followups.filter(
        status='Pending'
    ).count()

    completed_followups = followups.filter(
        status='Completed'
    ).count()

    referral_followups = followups.filter(
        status='For Referral'
    ).count()


    # ==========================================
    # AVERAGE BMI
    # ==========================================

    average_bmi = assessments.aggregate(
        Avg('bmi')
    )['bmi__avg']

    if average_bmi is None:
        average_bmi = 0

    average_bmi = round(
        float(average_bmi),
        2
    )


    # ==========================================
    # MONTHLY ASSESSMENTS
    # ==========================================

    monthly_data = (
        assessments
        .annotate(
            month=TruncMonth('assessment_date')
        )
        .values('month')
        .annotate(
            total=Count('id')
        )
        .order_by('month')
    )

    months = []
    monthly_counts = []

    for item in monthly_data:

        if item['month']:

            months.append(
                item['month'].strftime('%b %Y')
            )

            monthly_counts.append(
                item['total']
            )


    # ==========================================
    # MONTHLY NEEDS FOLLOW-UP
    # ==========================================

    monthly_flag_data = (
        assessments
        .filter(
            monitoring_flag='Needs Follow-up'
        )
        .annotate(
            month=TruncMonth('assessment_date')
        )
        .values('month')
        .annotate(
            total=Count('id')
        )
        .order_by('month')
    )

    flag_dictionary = {}

    for item in monthly_flag_data:

        if item['month']:

            month_name = item['month'].strftime(
                '%b %Y'
            )

            flag_dictionary[month_name] = (
                item['total']
            )

    monthly_needs_followup = []

    for month in months:

        monthly_needs_followup.append(
            flag_dictionary.get(
                month,
                0
            )
        )


    # ==========================================
    # CHART DATA
    # ==========================================

    status_chart_data = [
        normal,
        underweight,
        overweight,
        obese,
    ]

    monitoring_chart_data = [
        routine_monitoring,
        needs_followup,
    ]

    followup_chart_data = [
        pending_followups,
        completed_followups,
        referral_followups,
    ]


    # ==========================================
    # CONTEXT
    # ==========================================

    context = {

        'total_residents': total_residents,
        'total_assessments': total_assessments,
        'total_followups': total_followups,

        'assessed_residents': assessed_residents,
        'coverage': coverage,

        'normal': normal,
        'underweight': underweight,
        'overweight': overweight,
        'obese': obese,

        'routine_monitoring': routine_monitoring,
        'needs_followup': needs_followup,

        'pending_followups': pending_followups,
        'completed_followups': completed_followups,
        'referral_followups': referral_followups,

        'average_bmi': average_bmi,

        'months': months,
        'monthly_counts': monthly_counts,
        'monthly_needs_followup': monthly_needs_followup,

        'status_chart_data': status_chart_data,
        'monitoring_chart_data': monitoring_chart_data,
        'followup_chart_data': followup_chart_data,
    }


    return render(
        request,
        get_template(
            request,
            'analytics/dashboard.html',
            'admin_analytics/dashboard.html'
        ),
        context
    )