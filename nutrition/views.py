from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import NutritionAssessmentForm
from .models import NutritionAssessment
from activity_logs.models import ActivityLog


def get_template(request, staff_template, admin_template):
    """
    Return the correct template depending on the logged-in user.
    """
    if request.user.is_superuser:
        return admin_template
    return staff_template


@login_required(login_url='login')
def assessment_list(request):

    assessments = NutritionAssessment.objects.select_related(
        'resident'
    ).order_by('-assessment_date')

    context = {
        'assessments': assessments
    }

    return render(
        request,
        get_template(
            request,
            'nutrition/assessment_list.html',
            'admin_nutrition/assessment_list.html'
        ),
        context
    )


@login_required(login_url='login')
def add_assessment(request):

    if request.user.is_superuser:
        return redirect('assessment_list')

    if request.method == 'POST':

        form = NutritionAssessmentForm(request.POST)

        if form.is_valid():

            assessment = form.save()

            ActivityLog.objects.create(
                user=request.user,
                role="Admin" if request.user.is_superuser else "Staff",
                action="Add Assessment",
                description=(
                    f"Added nutrition assessment for "
                    f"{assessment.resident.first_name} "
                    f"{assessment.resident.last_name}"
                )
            )

            return redirect('assessment_list')

    else:

        form = NutritionAssessmentForm()

    context = {
        'form': form,
        'title': 'Add Nutrition Assessment'
    }

    return render(
        request,
        'nutrition/assessment_form.html',
        context
    )


@login_required(login_url='login')
def edit_assessment(request, pk):

    assessment = get_object_or_404(
        NutritionAssessment,
        pk=pk
    )

    if request.method == 'POST':

        form = NutritionAssessmentForm(
            request.POST,
            instance=assessment
        )

        if form.is_valid():

            assessment = form.save()

            ActivityLog.objects.create(
                user=request.user,
                role="Admin" if request.user.is_superuser else "Staff",
                action="Edit Assessment",
                description=(
                    f"Updated nutrition assessment for "
                    f"{assessment.resident.first_name} "
                    f"{assessment.resident.last_name}"
                )
            )

            return redirect('assessment_list')

    else:

        form = NutritionAssessmentForm(
            instance=assessment
        )

    context = {
        'form': form,
        'title': 'Edit Nutrition Assessment'
    }

    return render(
        request,
        get_template(
            request,
            'nutrition/assessment_form.html',
            'admin_nutrition/assessment_form.html'
        ),
        context
    )


@login_required(login_url='login')
def delete_assessment(request, pk):

    assessment = get_object_or_404(
        NutritionAssessment,
        pk=pk
    )

    if request.method == 'POST':

        resident_name = (
            f"{assessment.resident.first_name} "
            f"{assessment.resident.last_name}"
        )

        ActivityLog.objects.create(
            user=request.user,
            role="Admin" if request.user.is_superuser else "Staff",
            action="Delete Assessment",
            description=(
                f"Deleted nutrition assessment for {resident_name}"
            )
        )

        assessment.delete()

        return redirect('assessment_list')

    return render(
        request,
        get_template(
            request,
            'nutrition/assessment_delete.html',
            'admin_nutrition/assessment_delete.html'
        ),
        {
            'assessment': assessment
        }
    )