from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from residents.models import Resident
from nutrition.models import NutritionAssessment


@login_required(login_url='login')
def dashboard(request):

    # =========================
    # Population Summary
    # =========================

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

    # =========================
    # Nutrition Summary
    # =========================

    total_assessments = NutritionAssessment.objects.count()

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

    recent_residents = Resident.objects.order_by(
        '-created_at'
    )[:5]

    urgent_alerts = NutritionAssessment.objects.select_related(
        'resident'
    ).filter(
        nutritional_status__in=['Underweight', 'Obese']
    ).order_by(
        '-assessment_date'
    )[:5]

    context = {

        # Population
        'total_population': total_population,
        'total_male': total_male,
        'total_female': total_female,
        'children': children,
        'adolescents': adolescents,
        'adults': adults,
        'seniors': seniors,

        # Nutrition
        'total_assessments': total_assessments,
        'normal': normal,
        'underweight': underweight,
        'overweight': overweight,
        'obese': obese,
        'recent_residents': recent_residents,
        'urgent_alerts': urgent_alerts,
    }

    return render(
        request,
        'dashboard/dashboard.html',
        context
    )