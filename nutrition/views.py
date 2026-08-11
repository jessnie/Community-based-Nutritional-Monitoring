from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from .forms import (
    NutritionAssessmentForm,
    FollowUpRecordForm,
)

from .models import (
    NutritionAssessment,
    FollowUpRecord,
)

from activity_logs.models import ActivityLog


def get_template(request, staff_template, admin_template):

    if request.user.is_superuser:
        return admin_template

    return staff_template


def get_base_template(request):

    if request.user.is_superuser:
        return 'base_admin.html'

    return 'base_staff.html'


# =========================================================
# NUTRITION ASSESSMENT
# =========================================================

@login_required(login_url='login')
def assessment_list(request):

    assessments = (
        NutritionAssessment.objects
        .select_related(
            'resident',
            'assessed_by',
            'rule'
        )
        .order_by(
            '-assessment_date',
            '-created_at'
        )
    )

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

        form = NutritionAssessmentForm(
            request.POST
        )

        if form.is_valid():

            assessment = form.save(
                commit=False
            )

            assessment.assessed_by = (
                request.user
            )

            assessment.save()

            ActivityLog.objects.create(
                user=request.user,
                role=(
                    "Admin"
                    if request.user.is_superuser
                    else "Staff"
                ),
                action="Add Assessment",
                description=(
                    f"Added nutrition assessment for "
                    f"{assessment.resident.first_name} "
                    f"{assessment.resident.last_name}"
                )
            )

            return redirect(
                'assessment_list'
            )

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

            assessment = form.save(
                commit=False
            )

            if (
                assessment.assessed_by_id
                is None
            ):
                assessment.assessed_by = (
                    request.user
                )

            assessment.save()

            ActivityLog.objects.create(
                user=request.user,
                role=(
                    "Admin"
                    if request.user.is_superuser
                    else "Staff"
                ),
                action="Edit Assessment",
                description=(
                    f"Updated nutrition assessment for "
                    f"{assessment.resident.first_name} "
                    f"{assessment.resident.last_name}"
                )
            )

            return redirect(
                'assessment_list'
            )

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
            role=(
                "Admin"
                if request.user.is_superuser
                else "Staff"
            ),
            action="Delete Assessment",
            description=(
                f"Deleted nutrition assessment "
                f"for {resident_name}"
            )
        )

        assessment.delete()

        return redirect(
            'assessment_list'
        )

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


# =========================================================
# FOLLOW-UP MONITORING
# =========================================================

@login_required(login_url='login')
def followup_list(request):

    search = request.GET.get(
        'search',
        ''
    ).strip()

    status_filter = request.GET.get(
        'status',
        ''
    ).strip()

    followups = (
        FollowUpRecord.objects
        .select_related(
            'assessment',
            'assessment__resident',
            'assessment__assessed_by',
            'assessment__rule',
            'recorded_by',
        )
        .order_by(
            '-follow_up_date',
            '-created_at'
        )
    )

    if search:

        followups = followups.filter(

            Q(
                assessment__resident__resident_id__icontains=search
            )

            |

            Q(
                assessment__resident__first_name__icontains=search
            )

            |

            Q(
                assessment__resident__middle_name__icontains=search
            )

            |

            Q(
                assessment__resident__last_name__icontains=search
            )
        )

    if status_filter:

        followups = followups.filter(
            status=status_filter
        )

    context = {

        'followups': followups,

        'search': search,

        'status_filter': status_filter,

        'total_followups': (
            FollowUpRecord.objects.count()
        ),

        'pending_count': (
            FollowUpRecord.objects
            .filter(status='Pending')
            .count()
        ),

        'completed_count': (
            FollowUpRecord.objects
            .filter(status='Completed')
            .count()
        ),

        'referral_count': (
            FollowUpRecord.objects
            .filter(status='For Referral')
            .count()
        ),

        'base_template': (
            get_base_template(request)
        ),
    }

    return render(
        request,
        'nutrition/followup_list.html',
        context
    )


@login_required(login_url='login')
def add_followup(request):

    selected_assessment = (
        request.GET.get('assessment')
    )

    if request.method == 'POST':

        form = FollowUpRecordForm(
            request.POST
        )

        if form.is_valid():

            followup = form.save(
                commit=False
            )

            followup.recorded_by = (
                request.user
            )

            followup.save()

            return redirect(
                'followup_list'
            )

    else:

        initial = {}

        if selected_assessment:

            initial['assessment'] = (
                selected_assessment
            )

        form = FollowUpRecordForm(
            initial=initial
        )

    context = {

        'form': form,

        'title': 'Add Follow-Up Record',

        'base_template': (
            get_base_template(request)
        ),
    }

    return render(
        request,
        'nutrition/followup_form.html',
        context
    )


@login_required(login_url='login')
def edit_followup(request, pk):

    followup = get_object_or_404(
        FollowUpRecord,
        pk=pk
    )

    if request.method == 'POST':

        form = FollowUpRecordForm(
            request.POST,
            instance=followup
        )

        if form.is_valid():

            followup = form.save(
                commit=False
            )

            if (
                followup.recorded_by_id
                is None
            ):
                followup.recorded_by = (
                    request.user
                )

            followup.save()

            return redirect(
                'followup_list'
            )

    else:

        form = FollowUpRecordForm(
            instance=followup
        )

    context = {

        'form': form,

        'title': 'Edit Follow-Up Record',

        'followup': followup,

        'base_template': (
            get_base_template(request)
        ),
    }

    return render(
        request,
        'nutrition/followup_form.html',
        context
    )


@login_required(login_url='login')
def delete_followup(request, pk):

    followup = get_object_or_404(
        FollowUpRecord.objects.select_related(
            'assessment__resident'
        ),
        pk=pk
    )

    if request.method == 'POST':

        followup.delete()

        return redirect(
            'followup_list'
        )

    context = {

        'followup': followup,

        'base_template': (
            get_base_template(request)
        ),
    }

    return render(
        request,
        'nutrition/followup_delete.html',
        context
    )