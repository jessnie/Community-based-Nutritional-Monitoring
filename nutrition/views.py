from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from accounts.decorators import staff_required
from residents.models import Resident
from activity_logs.models import (
    ActivityLog,
    AdminArchivedRecord,
    RoleDeletedRecord,
    StaffArchivedRecord,
)
from activity_logs.utils import exclude_role_archived
from .forms import (
    NutritionAssessmentForm,
    FollowUpRecordForm,
)

from .models import (
    NutritionAssessment,
    FollowUpRecord,
)


def get_template(request, staff_template, admin_template):

    if request.user.is_superuser:
        return admin_template

    return staff_template


def get_base_template(request):

    if request.user.is_superuser:
        return 'base_admin.html'

    return 'base_staff.html'


def _visible_assessments(request):
    role = 'admin' if request.user.is_superuser else 'staff'
    return exclude_role_archived(NutritionAssessment.objects.all(), role)


def _visible_followups(request):
    role = 'admin' if request.user.is_superuser else 'staff'
    return exclude_role_archived(FollowUpRecord.objects.all(), role)


# =========================================================
# NUTRITION ASSESSMENT
# =========================================================

@login_required(login_url='login')
def assessment_list(request):

    assessments = (
        _visible_assessments(request)
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

    page_obj = Paginator(assessments, 5).get_page(
        request.GET.get('page')
    )

    context = {
        'assessments': assessments,
        'page_obj': page_obj,
        'pagination_aria_label': 'Nutrition assessment pages',
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

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

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
                role="Staff",
                action="Add Assessment",
                description=(
                    f"Added nutrition assessment for "
                    f"{assessment.resident.first_name} "
                    f"{assessment.resident.last_name}"
                )
            )

            if is_ajax:
                return JsonResponse({'success': True})
            return redirect(
                'assessment_list'
            )

    else:

        form = NutritionAssessmentForm()

    form.fields['resident'].queryset = exclude_role_archived(
        Resident.objects.all(),
        'staff',
    )

    context = {
        'form': form,
        'title': 'Add Nutrition Assessment'
    }

    if is_ajax:
        return render(
            request,
            'nutrition/_assessment_form_fields.html',
            context,
            status=400 if request.method == 'POST' else 200,
        )

    return render(
        request,
        'nutrition/assessment_form.html',
        context
    )


@login_required(login_url='login')
def edit_assessment(request, pk):

    if request.user.is_superuser:
        return redirect('assessment_list')

    assessment = get_object_or_404(
        _visible_assessments(request),
        pk=pk
    )
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

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
                role="Staff",
                action="Edit Assessment",
                description=(
                    f"Updated nutrition assessment for "
                    f"{assessment.resident.first_name} "
                    f"{assessment.resident.last_name}"
                )
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Update successfully',
                })
            return redirect('assessment_list')

    else:

        form = NutritionAssessmentForm(
            instance=assessment
        )

    context = {
        'form': form,
        'title': 'Edit Nutrition Assessment'
    }

    if is_ajax:
        return render(
            request,
            'nutrition/_assessment_form_fields.html',
            context,
            status=400 if request.method == 'POST' else 200,
        )

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
        _visible_assessments(request),
        pk=pk
    )

    action = request.POST.get(
        'action',
        request.GET.get('action', 'archive')
    )
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if action not in {'archive', 'delete'}:
        return redirect('assessment_list')

    if request.method == 'POST':

        resident_name = (
            f"{assessment.resident.first_name} "
            f"{assessment.resident.last_name}"
        )

        with transaction.atomic():
            role = 'admin' if request.user.is_superuser else 'staff'
            archive_model = (
                AdminArchivedRecord
                if role == 'admin'
                else StaffArchivedRecord
            )

            if action == 'delete':
                followup_ids = FollowUpRecord.all_objects.filter(
                    assessment=assessment
                ).values_list('pk', flat=True)
                related_markers = (
                    Q(record_type='assessment', record_id=assessment.pk)
                    | Q(record_type='followup', record_id__in=followup_ids)
                )
                archive_model.objects.filter(related_markers).delete()
                RoleDeletedRecord.objects.get_or_create(
                    role=role,
                    record_type='assessment',
                    record_id=assessment.pk,
                    defaults={'deleted_by': request.user},
                )
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin' if role == 'admin' else 'Staff',
                    action='Permanently Delete Record',
                    description=(
                        f"Permanently deleted nutrition assessment "
                        f"for {resident_name} from {role} records, "
                        "including related follow-ups."
                    ),
                )

            elif role == 'admin':

                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin',
                    action='Archive Record',
                    description=(
                        f"Archived nutrition assessment for {resident_name}"
                    )
                )

                archive_model.objects.get_or_create(
                    record_type='assessment',
                    record_id=assessment.pk,
                    defaults={'archived_by': request.user},
                )

            else:

                ActivityLog.objects.create(
                    user=request.user,
                    role='Staff',
                    action='Archive Record',
                    description=(
                        f"Removed nutrition assessment for {resident_name} "
                        "from staff lists."
                    ),
                )

                archive_model.objects.get_or_create(
                    record_type='assessment',
                    record_id=assessment.pk,
                    defaults={'archived_by': request.user},
                )

        if is_ajax:
            return JsonResponse({'success': True})
        return redirect('assessment_list')

    if is_ajax:
        return render(
            request,
            'nutrition/_assessment_delete_confirmation.html',
            {
                'assessment': assessment,
                'action': action,
            },
        )

    return render(
        request,
        get_template(
            request,
            'nutrition/assessment_delete.html',
            'admin_nutrition/assessment_delete.html'
        ),
        {
            'assessment': assessment,
            'action': action,
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
        _visible_followups(request)
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

    page_obj = Paginator(followups, 5).get_page(
        request.GET.get('page')
    )

    context = {

        'followups': page_obj,

        'page_obj': page_obj,

        'pagination_aria_label': 'Follow-up monitoring pages',

        'search': search,

        'status_filter': status_filter,

        'total_followups': (
            _visible_followups(request).count()
        ),

        'pending_count': (
            _visible_followups(request)
            .filter(status='Pending')
            .count()
        ),

        'completed_count': (
            _visible_followups(request)
            .filter(status='Completed')
            .count()
        ),

        'referral_count': (
            _visible_followups(request)
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


@staff_required
def add_followup(request):

    if request.user.is_superuser:
        return redirect('followup_list')

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    selected_assessment = (
        request.GET.get('assessment')
    )

    if request.method == 'POST':

        form = FollowUpRecordForm(
            request.POST
        )
        form.fields['assessment'].queryset = _visible_assessments(request)

        if form.is_valid():

            followup = form.save(
                commit=False
            )

            followup.recorded_by = (
                request.user
            )

            followup.save()

            if is_ajax:
                return JsonResponse({'success': True})
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
        form.fields['assessment'].queryset = _visible_assessments(request)

    context = {

        'form': form,

        'title': 'Add Follow-Up Record',

        'base_template': (
            get_base_template(request)
        ),
    }

    if is_ajax:
        return render(
            request,
            'nutrition/_followup_form_fields.html',
            context,
            status=400 if request.method == 'POST' else 200,
        )

    return render(
        request,
        'nutrition/followup_form.html',
        context
    )


@staff_required
def edit_followup(request, pk):

    if request.user.is_superuser:
        return redirect('followup_list')

    followup = get_object_or_404(
        _visible_followups(request),
        pk=pk
    )
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

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

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Update successfully',
                })
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

    if is_ajax:
        return render(
            request,
            'nutrition/_followup_form_fields.html',
            context,
            status=400 if request.method == 'POST' else 200,
        )

    return render(
        request,
        'nutrition/followup_form.html',
        context
    )



@login_required(login_url='login')
def delete_followup(request, pk):

    followup = get_object_or_404(
        _visible_followups(request).select_related(
            'assessment__resident'
        ),
        pk=pk
    )

    action = request.POST.get(
        'action',
        request.GET.get('action', 'archive')
    )
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if action not in {'archive', 'delete'}:
        return redirect('followup_list')

    if request.method == 'POST':

        resident_name = (
            f"{followup.assessment.resident.first_name} "
            f"{followup.assessment.resident.last_name}"
        )

        with transaction.atomic():
            role = 'admin' if request.user.is_superuser else 'staff'
            archive_model = (
                AdminArchivedRecord
                if role == 'admin'
                else StaffArchivedRecord
            )

            if action == 'delete':
                archive_model.objects.filter(
                    record_type='followup',
                    record_id=followup.pk,
                ).delete()
                RoleDeletedRecord.objects.get_or_create(
                    role=role,
                    record_type='followup',
                    record_id=followup.pk,
                    defaults={'deleted_by': request.user},
                )
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin' if role == 'admin' else 'Staff',
                    action='Permanently Delete Record',
                    description=(
                        f"Permanently deleted follow-up record for "
                        f"{resident_name} on {followup.follow_up_date} "
                        f"from {role} records."
                    ),
                )

            elif role == 'admin':

                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin',
                    action='Archive Record',
                    description=(
                        f"Archived follow-up record for {resident_name} "
                        f"on {followup.follow_up_date}"
                    )
                )

                archive_model.objects.get_or_create(
                    record_type='followup',
                    record_id=followup.pk,
                    defaults={'archived_by': request.user},
                )

            else:

                ActivityLog.objects.create(
                    user=request.user,
                    role='Staff',
                    action='Archive Record',
                    description=(
                        f"Removed follow-up record for {resident_name} "
                        f"on {followup.follow_up_date} from staff lists."
                    ),
                )

                archive_model.objects.get_or_create(
                    record_type='followup',
                    record_id=followup.pk,
                    defaults={'archived_by': request.user},
                )

        if is_ajax:
            return JsonResponse({'success': True})
        return redirect('followup_list')

    context = {
        'followup': followup,
        'action': action,
        'base_template': get_base_template(request),
    }

    if is_ajax:
        return render(
            request,
            'nutrition/_followup_delete_confirmation.html',
            context,
        )

    return render(
        request,
        'nutrition/followup_delete.html',
        context
    )
