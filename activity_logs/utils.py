from .models import (
    ActivityLog,
    AdminArchivedRecord,
    RoleDeletedRecord,
    StaffArchivedRecord,
)


def exclude_role_archived(queryset, role):
    model = queryset.model
    archive_model = {
        'admin': AdminArchivedRecord,
        'staff': StaffArchivedRecord,
    }[role]
    hidden_residents = archive_model.objects.filter(
        record_type='resident'
    ).values('record_id')
    deleted_residents = RoleDeletedRecord.objects.filter(
        role=role,
        record_type='resident',
    ).values('record_id')
    hidden_assessments = archive_model.objects.filter(
        record_type='assessment'
    ).values('record_id')
    deleted_assessments = RoleDeletedRecord.objects.filter(
        role=role,
        record_type='assessment',
    ).values('record_id')

    if model._meta.label_lower == 'residents.resident':
        return queryset.exclude(
            pk__in=hidden_residents
        ).exclude(
            pk__in=deleted_residents
        )

    if model._meta.label_lower == 'nutrition.nutritionassessment':
        return queryset.exclude(
            pk__in=hidden_assessments
        ).exclude(
            pk__in=deleted_assessments
        ).exclude(
            resident_id__in=hidden_residents
        ).exclude(
            resident_id__in=deleted_residents
        )

    if model._meta.label_lower == 'nutrition.followuprecord':
        hidden_followups = archive_model.objects.filter(
            record_type='followup'
        ).values('record_id')
        deleted_followups = RoleDeletedRecord.objects.filter(
            role=role,
            record_type='followup',
        ).values('record_id')
        return queryset.exclude(
            pk__in=hidden_followups
        ).exclude(
            pk__in=deleted_followups
        ).exclude(
            assessment_id__in=hidden_assessments
        ).exclude(
            assessment_id__in=deleted_assessments
        ).exclude(
            assessment__resident_id__in=hidden_residents
        ).exclude(
            assessment__resident_id__in=deleted_residents
        )

    return queryset


def exclude_staff_archived(queryset):
    return exclude_role_archived(queryset, 'staff')


def exclude_admin_archived(queryset):
    return exclude_role_archived(queryset, 'admin')


def log_activity(user, action, description):
    """
    Save an activity log for the given user.
    """

    if not user.is_authenticated:
        return

    role = "Admin" if user.is_superuser else "Staff"

    ActivityLog.objects.create(
        user=user,
        role=role,
        action=action,
        description=description
    )