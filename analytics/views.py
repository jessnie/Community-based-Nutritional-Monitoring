from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Avg, Max, Min
from django.db.models.functions import TruncMonth

from nutrition.models import NutritionAssessment
from residents.models import Resident


def get_template(request, staff_template, admin_template):
    """
    Return the correct template depending on the logged-in user.
    """
    if request.user.is_superuser:
        return admin_template
    return staff_template


@login_required(login_url='login')
def analytics_dashboard(request):

    # ==========================
    # NUTRITION STATUS COUNTS
    # ==========================

    normal = NutritionAssessment.objects.filter(
        nutritional_status='Normal'
    ).count()

    underweight = NutritionAssessment.objects.filter(
        nutritional_status='Underweight'
    ).count()

    overweight = NutritionAssessment.objects.filter(
        nutritional_status='Overweight'
    ).count()

    obese = NutritionAssessment.objects.filter(
        nutritional_status='Obese'
    ).count()

    # ==========================
    # TOTAL COUNTS
    # ==========================

    total_residents = Resident.objects.count()

    total_assessments = NutritionAssessment.objects.count()

    # ==========================
    # ADMIN ANALYTICS
    # ==========================

    male_residents = Resident.objects.filter(
        sex='Male'
    ).count()

    female_residents = Resident.objects.filter(
        sex='Female'
    ).count()

    intervention = underweight + obese

    average_bmi = NutritionAssessment.objects.aggregate(
        Avg('bmi')
    )['bmi__avg'] or 0

    highest_bmi = NutritionAssessment.objects.aggregate(
        Max('bmi')
    )['bmi__max'] or 0

    lowest_bmi = NutritionAssessment.objects.aggregate(
        Min('bmi')
    )['bmi__min'] or 0

    latest_assessment = NutritionAssessment.objects.order_by(
        '-assessment_date'
    ).first()

    coverage = 0

    if total_residents > 0:
        coverage = round(
            (total_assessments / total_residents) * 100,
            1
        )

    # ==========================
    # RECENT ASSESSMENTS
    # ==========================

    recent_assessments = (
        NutritionAssessment.objects
        .select_related('resident')
        .order_by('-assessment_date')[:5]
    )

    # ==========================
    # MONTHLY CHART DATA
    # ==========================

    monthly_data = (
        NutritionAssessment.objects
        .annotate(month=TruncMonth('assessment_date'))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
    )

    months = []
    monthly_counts = []

    for item in monthly_data:

        months.append(
            item['month'].strftime("%b %Y")
        )

        monthly_counts.append(
            item['total']
        )

    # ==========================
    # CONTEXT
    # ==========================

    context = {

        'normal': normal,
        'underweight': underweight,
        'overweight': overweight,
        'obese': obese,

        'total_residents': total_residents,
        'total_assessments': total_assessments,

        'male_residents': male_residents,
        'female_residents': female_residents,

        'intervention': intervention,

        'average_bmi': round(average_bmi, 2),
        'highest_bmi': highest_bmi,
        'lowest_bmi': lowest_bmi,

        'coverage': coverage,

        'latest_assessment': latest_assessment,

        'recent_assessments': recent_assessments,

        'months': months,
        'monthly_counts': monthly_counts,

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