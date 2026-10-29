from datetime import date

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import staff_required
from residents.models import Resident
from nutrition.models import (
    NutritionAssessment,
    FollowUpRecord,
    current_assessments,
)


def get_dashboard_summary():
    today = timezone.localdate()

    total_population = Resident.objects.count()

    total_male = Resident.objects.filter(
        sex='Male'
    ).count()

    total_female = Resident.objects.filter(
        sex='Female'
    ).count()

    children = 0
    adolescents = 0
    adults = 0
    seniors = 0

    for resident in Resident.objects.all():
        if resident.age <= 12:
            children += 1
        elif resident.age <= 17:
            adolescents += 1
        elif resident.age <= 59:
            adults += 1
        else:
            seniors += 1

    total_assessments = NutritionAssessment.objects.count()

    latest_assessments = current_assessments()

    normal = latest_assessments.filter(
        nutritional_status='Normal'
    ).count()

    underweight = latest_assessments.filter(
        nutritional_status='Underweight'
    ).count()

    overweight = latest_assessments.filter(
        nutritional_status='Overweight'
    ).count()

    obese = latest_assessments.filter(
        nutritional_status='Obese'
    ).count()

    current_month_index = today.year * 12 + today.month - 1
    trend_months = [
        (
            (current_month_index - offset) // 12,
            (current_month_index - offset) % 12 + 1,
        )
        for offset in reversed(range(12))
    ]
    trend_start = date(trend_months[0][0], trend_months[0][1], 1)
    monthly_assessment_totals = {
        (item['month'].year, item['month'].month): item['total']
        for item in NutritionAssessment.objects.filter(
            assessment_date__gte=trend_start,
            assessment_date__lte=today,
        ).annotate(
            month=TruncMonth('assessment_date')
        ).values(
            'month'
        ).annotate(
            total=Count('id')
        )
    }
    assessment_trend_labels = [
        date(year, month, 1).strftime('%b %Y')
        for year, month in trend_months
    ]
    assessment_trend_counts = [
        monthly_assessment_totals.get((year, month), 0)
        for year, month in trend_months
    ]
    nutrition_status_chart_data = [
        normal,
        underweight,
        overweight,
        obese,
    ]

    recent_residents = Resident.objects.order_by(
        '-created_at'
    )[:5]

    urgent_alerts = latest_assessments.select_related(
        'resident'
    ).filter(
        nutritional_status__in=['Underweight', 'Obese']
    ).order_by(
        '-assessment_date'
    )[:5]

    priority_cases = latest_assessments.select_related(
        'resident'
    ).filter(
        nutritional_status__in=['Underweight', 'Overweight', 'Obese']
    ).order_by(
        '-assessment_date',
        '-bmi'
    )[:6]

    pending_followups = FollowUpRecord.objects.filter(
        status='Pending'
    ).count()

    completed_followups = FollowUpRecord.objects.filter(
        status='Completed'
    ).count()

    referral_followups = FollowUpRecord.objects.filter(
        status='For Referral'
    ).count()

    recent_assessments = NutritionAssessment.objects.select_related(
        'resident'
    ).order_by(
        '-assessment_date',
        '-created_at'
    )[:5]

    recent_followups = FollowUpRecord.objects.select_related(
        'assessment',
        'assessment__resident'
    ).order_by(
        '-follow_up_date',
        '-created_at'
    )[:5]

    alert_messages = []
    recommendations = []

    if underweight > 0:
        alert_messages.append(
            f"{underweight} residents are currently underweight and need nutrition follow-up."
        )
        recommendations.append(
            "Priority review: schedule nutrition counseling for underweight residents within 48 hours."
        )

    if obese > 0:
        alert_messages.append(
            f"{obese} residents are currently classified as obese and need intervention review."
        )
        recommendations.append(
            "Intervention needed: arrange lifestyle and nutrition counseling for obese residents."
        )

    if overweight > 0:
        alert_messages.append(
            f"{overweight} residents are currently overweight and need routine nutrition follow-up."
        )
        recommendations.append(
            "Routine follow-up: review nutrition and activity goals for overweight residents."
        )

    if pending_followups > 0:
        recommendations.append(
            f"{pending_followups} follow-up actions remain pending and should be cleared this week."
        )

    if not recommendations:
        recommendations.append(
            "No immediate intervention required. Continue routine monitoring and annual assessment review."
        )

    priority_level = 'Low'
    priority_summary = 'No urgent intervention required.'

    if (
        underweight > 0
        or obese > 0
        or pending_followups > 0
        or referral_followups > 0
    ):
        priority_level = 'High'
        priority_summary = 'Immediate staff review recommended for high-risk nutrition cases and pending follow-ups.'
    elif overweight > 0 or normal > 0:
        priority_level = 'Medium'
        priority_summary = 'Routine monitoring is active; continue scheduled follow-up review.'

    summary = {
        'total_population': total_population,
        'total_male': total_male,
        'total_female': total_female,
        'children': children,
        'adolescents': adolescents,
        'adults': adults,
        'seniors': seniors,
        'total_assessments': total_assessments,
        'normal': normal,
        'underweight': underweight,
        'overweight': overweight,
        'obese': obese,
        'nutrition_status_chart_data': nutrition_status_chart_data,
        'assessment_trend_labels': assessment_trend_labels,
        'assessment_trend_counts': assessment_trend_counts,
        'recent_residents': [
            {
                'name': f"{resident.first_name} {resident.last_name}",
                'address': resident.address,
            } for resident in recent_residents
        ],
        'recent_assessments': [
            {
                'resident_name': (
                    f"{assessment.resident.first_name} {assessment.resident.last_name}"
                ),
                'assessment_date': assessment.assessment_date.isoformat(),
                'nutritional_status': assessment.nutritional_status,
            }
            for assessment in recent_assessments
        ],
        'recent_followups': [
            {
                'resident_name': (
                    f"{followup.assessment.resident.first_name} "
                    f"{followup.assessment.resident.last_name}"
                ),
                'follow_up_date': followup.follow_up_date.isoformat(),
                'status': followup.status,
            }
            for followup in recent_followups
        ],
        'urgent_alerts': [
            {
                'name': f"{assessment.resident.first_name} {assessment.resident.last_name}",
                'status': assessment.nutritional_status,
                'date': assessment.assessment_date.strftime('%Y-%m-%d'),
            } for assessment in urgent_alerts
        ],
        'priority_cases': [
            {
                'name': f"{assessment.resident.first_name} {assessment.resident.last_name}",
                'status': assessment.nutritional_status,
                'bmi': float(assessment.bmi),
                'date': assessment.assessment_date.strftime('%Y-%m-%d'),
                'flag': assessment.monitoring_flag,
                'action': (
                    'Schedule nutrition counseling'
                    if assessment.nutritional_status == 'Underweight'
                    else 'Urgent intervention review'
                    if assessment.nutritional_status == 'Obese'
                    else 'Review nutrition and activity goals'
                ),
            } for assessment in priority_cases
        ],
        'decision_support': alert_messages,
        'recommendations': recommendations,
        'pending_followups': pending_followups,
        'completed_followups': completed_followups,
        'referral_followups': referral_followups,
        'priority_level': priority_level,
        'priority_summary': priority_summary,
        'priority_actions': recommendations[:3],
        'last_updated': __import__('datetime').datetime.now().strftime('%b %d, %Y %I:%M %p'),
    }

    return summary


@staff_required
def dashboard(request):
    context = get_dashboard_summary()
    return render(
        request,
        'dashboard/dashboard.html',
        context
    )


@staff_required
def live_dashboard_stats(request):
    return JsonResponse(get_dashboard_summary())