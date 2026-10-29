from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from nutrition.models import NutritionAssessment, FollowUpRecord, current_assessments
from residents.models import Resident
from activity_logs.models import ActivityLog


def admin_check(user):
    return user.is_superuser


@user_passes_test(admin_check, login_url='login')
def admin_dashboard(request):
    latest_assessments = current_assessments()
    context = {
        'total_residents': Resident.objects.count(),
        'total_assessments': NutritionAssessment.objects.count(),
        'malnutrition_cases': latest_assessments.filter(
            nutritional_status__in=['Underweight', 'Overweight', 'Obese']
        ).count(),
        'pending_followups': FollowUpRecord.objects.filter(
            status__in=['Pending', 'For Referral']
        ).count(),
    }
    return render(request, 'admin_dashboard/admin_dashboard.html', context)


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
            return redirect('archived_records')

        model, label = model_info
        record = get_object_or_404(
            model.all_objects,
            pk=request.POST.get('record_id'),
            archived_at__isnull=False,
        )

        with transaction.atomic():
            if action == 'restore':
                model.all_objects.filter(pk=record.pk).update(
                    archived_at=None,
                    updated_at=timezone.now(),
                )
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin',
                    action='Restore Record',
                    description=f'Restored {label} record (ID: {record.pk}).',
                )
            else:
                ActivityLog.objects.create(
                    user=request.user,
                    role='Admin',
                    action='Permanently Delete Record',
                    description=f'Permanently deleted {label} record (ID: {record.pk}).',
                )
                record.delete()

        if action == 'restore':
            messages.success(request, 'The record was restored.')
        else:
            messages.success(request, 'The record was permanently deleted.')

        return redirect('archived_records')

    records = []
    for record_type, (model, label) in record_models.items():
        queryset = model.all_objects.filter(archived_at__isnull=False)
        if model is NutritionAssessment:
            queryset = queryset.select_related('resident')
        elif model is FollowUpRecord:
            queryset = queryset.select_related('assessment__resident')

        for record in queryset:
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
                'record_type': record_type,
                'label': label.title(),
                'object_id': record.pk,
                'summary': summary,
                'archived_at': record.archived_at,
                'includes_children': isinstance(record, Resident),
                'includes_followups': isinstance(record, NutritionAssessment),
            })

    records.sort(key=lambda item: item['archived_at'], reverse=True)
    return render(
        request,
        'admin_dashboard/archived_records.html',
        {'records': records},
    )