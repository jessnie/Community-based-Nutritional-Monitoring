from django.db import models
from django.contrib.auth.models import User


class ActivityLog(models.Model):

    ACTION_CHOICES = [
        ('Login', 'Login'),
        ('Logout', 'Logout'),
        ('Add Resident', 'Add Resident'),
        ('Edit Resident', 'Edit Resident'),
        ('Delete Resident', 'Delete Resident'),
        ('Archive Record', 'Archive Record'),
        ('Restore Record', 'Restore Record'),
        ('Permanently Delete Record', 'Permanently Delete Record'),
        ('Add Assessment', 'Add Assessment'),
        ('Edit Assessment', 'Edit Assessment'),
        ('Delete Assessment', 'Delete Assessment'),
        ('Generate Report', 'Generate Report'),
        ('Export PDF', 'Export PDF'),
        ('Export Excel', 'Export Excel'),
        ('Add User', 'Add User'),
        ('Edit User', 'Edit User'),
        ('Delete User', 'Delete User'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES
    )

    description = models.TextField()

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action}"


class StaffArchivedRecord(models.Model):

    RECORD_TYPES = [
        ('resident', 'Resident'),
        ('assessment', 'Nutrition Assessment'),
        ('followup', 'Follow-Up Record'),
    ]

    record_type = models.CharField(max_length=20, choices=RECORD_TYPES)
    record_id = models.PositiveBigIntegerField()
    archived_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['record_type', 'record_id'],
                name='unique_staff_archived_record',
            ),
        ]


class AdminArchivedRecord(models.Model):

    RECORD_TYPES = StaffArchivedRecord.RECORD_TYPES

    record_type = models.CharField(max_length=20, choices=RECORD_TYPES)
    record_id = models.PositiveBigIntegerField()
    archived_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['record_type', 'record_id'],
                name='unique_admin_archived_record',
            ),
        ]


class RoleDeletedRecord(models.Model):

    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    RECORD_TYPES = StaffArchivedRecord.RECORD_TYPES

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    record_type = models.CharField(max_length=20, choices=RECORD_TYPES)
    record_id = models.PositiveBigIntegerField()
    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'record_type', 'record_id'],
                name='unique_role_deleted_record',
            ),
        ]