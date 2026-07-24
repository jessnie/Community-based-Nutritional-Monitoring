from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from residents.models import Resident
from nutrition.models import NutritionAssessment


@login_required(login_url='login')
def dashboard(request):

    total_residents = Resident.objects.count()

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

    context = {
        'total_residents': total_residents,
        'total_assessments': total_assessments,
        'normal': normal,
        'underweight': underweight,
        'overweight': overweight,
        'obese': obese,
    }

    return render(
        request,
        'dashboard/dashboard.html',
        context
    )