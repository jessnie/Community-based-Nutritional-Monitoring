from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import staff_required
from .forms import ResidentForm
from .models import Resident
from nutrition.models import NutritionAssessment
from activity_logs.models import ActivityLog


def get_template(request, staff_template, admin_template):
    """
    Return the correct template depending on the logged-in user.
    """
    if request.user.is_superuser:
        return admin_template

    return staff_template


@login_required(login_url='login')
def resident_list(request):

    search = request.GET.get('search', '')

    residents = Resident.objects.select_related(
        'created_by'
    ).all()

    if search:

        residents = residents.filter(
            Q(resident_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(middle_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(address__icontains=search)
        )

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

            return redirect(
                'resident_list'
            )

    else:

        form = ResidentForm()

    context = {
        'form': form,
        'title': 'Add Resident'
    }

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
    Resident.objects,
        pk=pk
    )

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

            return redirect(
                'resident_list'
            )

    else:

        form = ResidentForm(
            instance=resident
        )

    context = {
        'form': form,
        'title': 'Edit Resident'
    }

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

    resident = get_object_or_404(
        Resident,
        pk=pk
    )

    action = request.POST.get(
        'action',
        request.GET.get('action', 'archive')
    )
    if action not in {'archive', 'delete'}:
        return redirect('resident_list')

    if request.method == 'POST':

        resident_name = (
            f"{resident.first_name} "
            f"{resident.last_name}"
        )

        with transaction.atomic():
            if action == 'delete':
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin' if request.user.is_superuser else 'Staff',
                    action='Permanently Delete Record',
                    description=(
                        f"Permanently deleted resident {resident_name} "
                        f"(ID: {resident.resident_id}) and related nutrition history."
                    ),
                )
                resident.delete()
            else:
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin' if request.user.is_superuser else 'Staff',
                    action='Archive Record',
                    description=(
                        f"Archived resident "
                        f"{resident_name} (ID: {resident.resident_id})"
                    )
                )

                archived_at = timezone.now()
                Resident.all_objects.filter(pk=resident.pk).update(
                    archived_at=archived_at,
                    updated_at=archived_at,
                )

        return redirect(
            'resident_list'
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

    resident = get_object_or_404(
        Resident.objects.select_related(
            'created_by'
        ),
        pk=pk
    )

    assessments = (
        NutritionAssessment.objects
        .filter(
            resident=resident
        )
        .select_related(
            'assessed_by',
            'rule'
        )
        .prefetch_related(
            'follow_ups__recorded_by'
        )
        .order_by(
            '-assessment_date',
            '-created_at'
        )
    )

    context = {
        'resident': resident,
        'assessments': assessments,
    }

    return render(
        request,
        get_template(
            request,
            'residents/resident_profile.html',
            'admin_residents/resident_profile.html'
        ),
        context
    )