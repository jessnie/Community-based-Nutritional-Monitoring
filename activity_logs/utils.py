from .models import ActivityLog


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