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