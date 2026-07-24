from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

from residents.models import Resident
from nutrition.models import NutritionAssessment


def admin_check(user):
    return user.is_superuser


@user_passes_test(admin_check, login_url='login')
def admin_dashboard(request):

    # Total residents
    total_residents = Resident.objects.count()

    # Total assessments
    total_assessments = NutritionAssessment.objects.count()

    # Count residents who need monitoring
    malnutrition_cases = NutritionAssessment.objects.filter(
        nutritional_status__in=[
            "Underweight",
            "Obese"
        ]
    ).count()

    context = {
        "total_residents": total_residents,
        "total_assessments": total_assessments,
        "malnutrition_cases": malnutrition_cases,
    }

    return render(
        request,
        "admin_dashboard/admin_dashboard.html",
        context
    )