from datetime import date

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import staff_required
from .forms import ResidentForm
from .models import Resident
from nutrition.models import FollowUpRecord, NutritionAssessment
from activity_logs.models import (
    ActivityLog,
    AdminArchivedRecord,
    RoleDeletedRecord,
    StaffArchivedRecord,
)
from activity_logs.utils import exclude_role_archived


def get_template(request, staff_template, admin_template):
    """
    Return the correct template depending on the logged-in user.
    """
    if request.user.is_superuser:
        return admin_template

    return staff_template


def _visible_residents(request):
    role = 'admin' if request.user.is_superuser else 'staff'
    return exclude_role_archived(Resident.objects.all(), role)


def _birth_date_for_age(age):
    today = date.today()
    try:
        return today.replace(year=today.year - age)
    except ValueError:
        return today.replace(year=today.year - age, day=28)


@login_required(login_url='login')
def resident_list(request):

    search = request.GET.get('search', '')
    classification = request.GET.get('classification', '')

    residents = Resident.objects.select_related(
        'created_by'
    ).all()
    residents = exclude_role_archived(
        residents,
        'admin' if request.user.is_superuser else 'staff',
    )

    if search:

        residents = residents.filter(
            Q(resident_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(middle_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(address__icontains=search)
        )

    today = date.today()
    classification_filters = {
        'kids': Q(
            birth_date__gt=_birth_date_for_age(13),
            birth_date__lte=today,
        ),
        'teens': Q(
            birth_date__lte=_birth_date_for_age(13),
            birth_date__gt=_birth_date_for_age(18),
        ),
        'adults': Q(
            birth_date__lte=_birth_date_for_age(18),
            birth_date__gt=_birth_date_for_age(60),
        ),
        'senior': Q(birth_date__lte=_birth_date_for_age(60)),
    }

    if classification in classification_filters:
        residents = residents.filter(classification_filters[classification])
    else:
        classification = ''

    paginator = Paginator(
        residents,
        10
    )

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        'page_obj': page_obj,
        'search': search,
        'classification': classification,
    }

    return render(
        request,
        get_template(
            request,
            'residents/resident_list.html',
            'admin_residents/resident_list.html'
        ),
        context
    )


@staff_required
def add_resident(request):

    if request.user.is_superuser:
        return redirect('resident_list')

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':

        form = ResidentForm(
            request.POST
        )

        if form.is_valid():

            resident = form.save(
                commit=False
            )

            # Automatically record who created the resident
            resident.created_by = request.user

            resident.save()

            ActivityLog.objects.create(
                user=request.user,
                role="Staff",
                action="Add Resident",
                description=(
                    f"Added resident "
                    f"{resident.first_name} "
                    f"{resident.last_name} "
                    f"(ID: {resident.resident_id})"
                )
            )

            if is_ajax:
                return JsonResponse({'success': True})
            return redirect('resident_list')

    else:

        form = ResidentForm()

    context = {
        'form': form,
        'title': 'Add Resident'
    }

    if is_ajax:
        return render(
            request,
            'residents/_resident_form_fields.html',
            context,
            status=400 if request.method == 'POST' else 200,
        )

    return render(
        request,
        get_template(
            request,
            'residents/resident_form.html',
            'admin_residents/resident_form.html'
        ),
        context
    )


@staff_required
def edit_resident(request, pk):

    if request.user.is_superuser:
        return redirect('resident_list')

    resident = get_object_or_404(
        _visible_residents(request),
        pk=pk
    )
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':

        form = ResidentForm(
            request.POST,
            instance=resident
        )

        if form.is_valid():

            resident = form.save(
                commit=False
            )

            # Old records may not have created_by
            if resident.created_by_id is None:
                resident.created_by = request.user

            resident.save()

            ActivityLog.objects.create(
                user=request.user,
                role=(
                    "Admin"
                    if request.user.is_superuser
                    else "Staff"
                ),
                action="Edit Resident",
                description=(
                    f"Updated resident "
                    f"{resident.first_name} "
                    f"{resident.last_name}"
                )
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Update successfully',
                })
            return redirect('resident_list')

    else:

        form = ResidentForm(
            instance=resident
        )

    context = {
        'form': form,
        'title': 'Edit Resident'
    }

    if is_ajax:
        return render(
            request,
            'residents/_resident_form_fields.html',
            context,
            status=400 if request.method == 'POST' else 200,
        )

    return render(
        request,
        get_template(
            request,
            'residents/resident_form.html',
            'admin_residents/resident_form.html'
        ),
        context
    )



@login_required(login_url='login')
def delete_resident(request, pk):

    residents = _visible_residents(request)

    resident = get_object_or_404(
        residents,
        pk=pk
    )

    action = request.POST.get(
        'action',
        request.GET.get('action', 'archive')
    )
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if action not in {'archive', 'delete'}:
        return redirect('resident_list')

    if request.method == 'POST':

        resident_name = (
            f"{resident.first_name} "
            f"{resident.last_name}"
        )

        with transaction.atomic():
            role = 'admin' if request.user.is_superuser else 'staff'
            archive_model = (
                AdminArchivedRecord
                if role == 'admin'
                else StaffArchivedRecord
            )

            if action == 'delete':
                assessment_ids = NutritionAssessment.all_objects.filter(
                    resident=resident
                ).values_list('pk', flat=True)
                followup_ids = FollowUpRecord.all_objects.filter(
                    assessment__resident=resident
                ).values_list('pk', flat=True)
                related_markers = (
                    Q(record_type='resident', record_id=resident.pk)
                    | Q(record_type='assessment', record_id__in=assessment_ids)
                    | Q(record_type='followup', record_id__in=followup_ids)
                )
                archive_model.objects.filter(related_markers).delete()
                RoleDeletedRecord.objects.get_or_create(
                    role=role,
                    record_type='resident',
                    record_id=resident.pk,
                    defaults={'deleted_by': request.user},
                )
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin' if role == 'admin' else 'Staff',
                    action='Permanently Delete Record',
                    description=(
                        f"Permanently deleted resident {resident_name} "
                        f"(ID: {resident.resident_id}) from {role} records."
                    ),
                )

            elif role == 'admin':

                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin',
                    action='Archive Record',
                    description=(
                        f"Archived resident {resident_name} "
                        f"(ID: {resident.resident_id})"
                    )
                )

                archive_model.objects.get_or_create(
                    record_type='resident',
                    record_id=resident.pk,
                    defaults={'archived_by': request.user},
                )

            else:

                ActivityLog.objects.create(
                    user=request.user,
                    role='Staff',
                    action='Archive Record',
                    description=(
                        f"Removed resident {resident_name} "
                        f"(ID: {resident.resident_id}) from staff lists."
                    ),
                )

                archive_model.objects.get_or_create(
                    record_type='resident',
                    record_id=resident.pk,
                    defaults={'archived_by': request.user},
                )

        if is_ajax:
            return JsonResponse({'success': True})
        return redirect('resident_list')

    if is_ajax:
        return render(
            request,
            'residents/_resident_delete_confirmation.html',
            {
                'resident': resident,
                'action': action,
            },
        )

    return render(
        request,
        get_template(
            request,
            'residents/resident_delete.html',
            'admin_residents/resident_delete.html'
        ),
        {
            'resident': resident,
            'action': action,
        }
    )




@login_required(login_url='login')
def view_resident(request, pk):

    role = 'admin' if request.user.is_superuser else 'staff'

    residents = exclude_role_archived(
        Resident.objects.select_related('created_by'),
        role,
    )

    resident = get_object_or_404(
        residents,
        pk=pk
    )

    # Get visible follow-up records
    followups = FollowUpRecord.objects.select_related(
        'recorded_by'
    )

    followups = exclude_role_archived(
        followups,
        role
    )

    # Get visible nutrition assessments
    assessments = NutritionAssessment.objects.filter(
        resident=resident
    ).select_related(
        'assessed_by',
        'rule'
    ).prefetch_related(
        Prefetch(
            'follow_ups',
            queryset=followups,
        )
    ).order_by(
        '-assessment_date',
        '-created_at'
    )

    assessments = exclude_role_archived(
        assessments,
        role
    )

    context = {
        'resident': resident,
        'assessments': assessments,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(
            request,
            'residents/_resident_profile.html',
            context,
        )

    return render(
        request,
        get_template(
            request,
            'residents/resident_profile.html',
            'admin_residents/resident_profile.html'
        ),
        context
    )
