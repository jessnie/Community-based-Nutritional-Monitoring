from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from nutrition.models import (
    NutritionAssessment,
    FollowUpRecord,
    current_assessments,
)
from residents.models import Resident
from activity_logs.models import (
    ActivityLog,
    AdminArchivedRecord,
    RoleDeletedRecord,
)
from activity_logs.utils import exclude_role_archived


def admin_check(user):
    return user.is_superuser


@user_passes_test(admin_check, login_url='login')
def admin_dashboard(request):
    residents = exclude_role_archived(Resident.objects.all(), 'admin')
    assessments = exclude_role_archived(NutritionAssessment.objects.all(), 'admin')
    followups = exclude_role_archived(FollowUpRecord.objects.all(), 'admin')
    latest_assessments = exclude_role_archived(current_assessments(), 'admin')
    assessed_resident_ids = assessments.values('resident_id')
    residents_without_assessment = residents.exclude(
        pk__in=assessed_resident_ids
    )
    context = {
        'total_residents': residents.count(),
        'total_assessments': assessments.count(),
        'residents_without_assessment': residents_without_assessment.count(),
        'malnutrition_cases': latest_assessments.filter(
            nutritional_status__in=['Underweight', 'Overweight', 'Obese']
        ).count(),
        'pending_followups': followups.filter(
            status__in=['Pending', 'For Referral']
        ).count(),
    }
    return render(request, 'admin_dashboard/admin_dashboard.html', context)


@user_passes_test(admin_check, login_url='login')
def unassessed_residents(request):
    residents = exclude_role_archived(Resident.objects.all(), 'admin')
    assessed_resident_ids = exclude_role_archived(
        NutritionAssessment.objects.all(),
        'admin',
    ).values('resident_id')
    residents = residents.exclude(
        pk__in=assessed_resident_ids
    ).order_by('last_name', 'first_name')
    page_obj = Paginator(residents, 10).get_page(request.GET.get('page'))

    return render(
        request,
        'admin_dashboard/unassessed_residents.html',
        {
            'page_obj': page_obj,
            'pagination_aria_label': 'Residents without assessment pages',
        },
    )


@user_passes_test(admin_check, login_url='login')
def archived_records(request):
    record_models = {
        'resident': (Resident, 'resident'),
        'assessment': (NutritionAssessment, 'assessment'),
        'followup': (FollowUpRecord, 'follow-up'),
    }

    if request.method == 'POST':
        record_type = request.POST.get('record_type')
        action = request.POST.get('action')
        model_info = record_models.get(record_type)

        if model_info is None or action not in {'restore', 'delete'}:
            messages.error(request, 'Choose a valid archived record action.')
            return redirect(request.get_full_path())

        model, label = model_info
        record_id = request.POST.get('record_id')
        marker = AdminArchivedRecord.objects.filter(
            record_type=record_type,
            record_id=record_id,
        ).first()
        record_queryset = model.all_objects.filter(pk=record_id)
        if marker is None:
            record_queryset = record_queryset.filter(archived_at__isnull=False)
        record = get_object_or_404(record_queryset)

        with transaction.atomic():
            if action == 'restore':
                if marker is not None:
                    marker.delete()
                if record.archived_at is not None:
                    model.all_objects.filter(pk=record.pk).update(
                        archived_at=None,
                        updated_at=timezone.now(),
                    )
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin',
                    action='Restore Record',
                    description=f'Restored {label} record (ID: {record.pk}) to admin lists.',
                )
            else:
                AdminArchivedRecord.objects.filter(
                    _related_marker_filter(record)
                ).delete()
                RoleDeletedRecord.objects.get_or_create(
                    role='admin',
                    record_type=record_type,
                    record_id=record.pk,
                    defaults={'deleted_by': request.user},
                )
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin',
                    action='Permanently Delete Record',
                    description=(
                        f'Permanently deleted {label} record (ID: {record.pk}) '
                        'from admin records.'
                    ),
                )

        if action == 'restore':
            messages.success(request, 'The record was restored.')
        else:
            messages.success(request, 'The record was permanently deleted from admin records.')

        return redirect(request.get_full_path())

    records = []
    seen_records = set()
    for record_type, (model, label) in record_models.items():
        markers = AdminArchivedRecord.objects.filter(
            record_type=record_type
        ).order_by('-archived_at')
        for marker in markers:
            record = model.all_objects.filter(pk=marker.record_id).first()
            if record is None:
                continue
            records.append(_record_row(record_type, label, record, marker.archived_at))
            seen_records.add((record_type, record.pk))

        queryset = model.all_objects.filter(archived_at__isnull=False)
        if model is NutritionAssessment:
            queryset = queryset.select_related('resident')
        elif model is FollowUpRecord:
            queryset = queryset.select_related('assessment__resident')

        for record in queryset:
            if (record_type, record.pk) in seen_records:
                continue
            records.append(_record_row(record_type, label, record, record.archived_at))

    records.sort(key=lambda item: item['archived_at'], reverse=True)
    page_obj = Paginator(records, 5).get_page(
        request.GET.get('page')
    )
    return render(
        request,
        'admin_dashboard/archived_records.html',
        {
            'records': page_obj,
            'page_obj': page_obj,
            'pagination_aria_label': 'Archived records pages',
        },
    )


def _record_row(record_type, label, record, archived_at):
    if isinstance(record, Resident):
        summary = f'{record.resident_id} - {record.first_name} {record.last_name}'
    elif isinstance(record, NutritionAssessment):
        summary = (
            f'{record.resident.first_name} {record.resident.last_name} - '
            f'assessment on {record.assessment_date}'
        )
    else:
        summary = (
            f'{record.assessment.resident.first_name} '
            f'{record.assessment.resident.last_name} - '
            f'follow-up on {record.follow_up_date}'
        )
    return {
        'record_type': record_type,
        'label': label.title(),
        'object_id': record.pk,
        'summary': summary,
        'archived_at': archived_at,
        'includes_children': isinstance(record, Resident),
        'includes_followups': isinstance(record, NutritionAssessment),
    }


def _related_marker_filter(record):
    if isinstance(record, Resident):
        assessment_ids = NutritionAssessment.all_objects.filter(
            resident=record
        ).values_list('pk', flat=True)
        followup_ids = FollowUpRecord.all_objects.filter(
            assessment__resident=record
        ).values_list('pk', flat=True)
        return (
            Q(record_type='resident', record_id=record.pk)
            | Q(record_type='assessment', record_id__in=assessment_ids)
            | Q(record_type='followup', record_id__in=followup_ids)
        )
    if isinstance(record, NutritionAssessment):
        followup_ids = FollowUpRecord.all_objects.filter(
            assessment=record
        ).values_list('pk', flat=True)
        return (
            Q(record_type='assessment', record_id=record.pk)
            | Q(record_type='followup', record_id__in=followup_ids)
        )
    return Q(record_type='followup', record_id=record.pk)
