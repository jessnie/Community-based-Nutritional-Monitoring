from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import staff_required
from nutrition.models import FollowUpRecord, NutritionAssessment
from residents.models import Resident
from .models import ActivityLog, RoleDeletedRecord, StaffArchivedRecord


@login_required(login_url='login')
def activity_logs(request):

    logs = ActivityLog.objects.select_related(
        'user'
    ).all()
    paginator = Paginator(logs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'total_logs': paginator.count,
    }

    return render(

        request,

        'activity_logs/dashboard.html',

        context

    )


@staff_required
def staff_archived_records(request):
    record_models = {
        'resident': (Resident, 'Resident'),
        'assessment': (NutritionAssessment, 'Nutrition Assessment'),
        'followup': (FollowUpRecord, 'Follow-Up Record'),
    }

    if request.method == 'POST':
        record_type = request.POST.get('record_type')
        record_id = request.POST.get('record_id')
        action = request.POST.get('action')
        if action not in {'restore', 'delete'} or record_type not in record_models:
            messages.error(request, 'Choose a valid archived record action.')
            return redirect(request.get_full_path())

        marker = get_object_or_404(
            StaffArchivedRecord,
            record_type=record_type,
            record_id=record_id,
        )
        record_model, label = record_models[record_type]
        record = get_object_or_404(record_model.all_objects, pk=marker.record_id)

        with transaction.atomic():
            if action == 'restore':
                marker.delete()
                ActivityLog.objects.create(
                    user=request.user,
                    role='Staff',
                    action='Restore Record',
                    description=f'Restored {label.lower()} record (ID: {record.pk}) to staff lists.',
                )
            else:
                StaffArchivedRecord.objects.filter(
                    _related_staff_archive_filter(record)
                ).delete()
                RoleDeletedRecord.objects.get_or_create(
                    role='staff',
                    record_type=record_type,
                    record_id=record.pk,
                    defaults={'deleted_by': request.user},
                )
                ActivityLog.objects.create(
                    user=request.user,
                    role='Staff',
                    action='Permanently Delete Record',
                    description=(
                        f'Permanently deleted {label.lower()} record '
                        f'(ID: {record.pk}) from staff records.'
                    ),
                )

        if action == 'restore':
            messages.success(request, 'The record was restored to staff lists.')
        else:
            messages.success(request, 'The record was permanently deleted from staff records.')
        return redirect(request.get_full_path())

    records = []
    for marker in StaffArchivedRecord.objects.order_by('-archived_at'):
        record_model, label = record_models[marker.record_type]
        record = record_model.all_objects.filter(pk=marker.record_id).first()
        if record is None:
            continue

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

        records.append({
            'record_type': marker.record_type,
            'object_id': marker.record_id,
            'label': label,
            'summary': summary,
            'archived_at': marker.archived_at,
        })

    page_obj = Paginator(records, 5).get_page(
        request.GET.get('page')
    )

    return render(
        request,
        'activity_logs/staff_archived_records.html',
        {
            'records': page_obj,
            'page_obj': page_obj,
            'pagination_aria_label': 'Archived records pages',
        },
    )


def _related_staff_archive_filter(record):
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