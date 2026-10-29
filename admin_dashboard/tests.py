from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from activity_logs.models import ActivityLog
from residents.models import Resident


class ArchivedRecordManagementTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='archiveadmin',
            email='archiveadmin@example.com',
            password='test-password',
        )
        self.staff = get_user_model().objects.create_user(
            username='archivestaff',
            password='test-password',
        )
        self.resident = Resident.all_objects.create(
            first_name='Archived',
            last_name='Resident',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
            archived_at=timezone.now(),
        )

    def test_only_admin_can_open_archived_records(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('archived_records'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            reverse('login') + '?next=' + reverse('archived_records'),
        )

    def test_admin_can_restore_archived_record(self):
        self.client.force_login(self.admin)

        page = self.client.get(reverse('archived_records'))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, self.resident.resident_id)

        response = self.client.post(reverse('archived_records'), {
            'record_type': 'resident',
            'record_id': self.resident.pk,
            'action': 'restore',
        })

        self.assertRedirects(response, reverse('archived_records'))
        self.resident.refresh_from_db()
        self.assertIsNone(self.resident.archived_at)
        self.assertTrue(Resident.objects.filter(pk=self.resident.pk).exists())

    def test_admin_can_permanently_delete_an_archived_record(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('archived_records'), {
            'record_type': 'resident',
            'record_id': self.resident.pk,
            'action': 'delete',
        })

        self.assertRedirects(response, reverse('archived_records'))
        self.assertFalse(Resident.all_objects.filter(pk=self.resident.pk).exists())


class AuditTrailLabelTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='auditadmin',
            email='auditadmin@example.com',
            password='test-password',
        )
        self.client.force_login(self.admin)

    def test_admin_dashboard_uses_audit_trail_label(self):
        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Audit Trail')
        self.assertNotContains(response, 'Activity Logs')

    def test_audit_page_uses_audit_trail_label(self):
        response = self.client.get(reverse('activity_logs'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Audit Trail')
        self.assertContains(response, 'Audit History')
        self.assertNotContains(response, 'Activity Logs')

    def test_audit_page_paginates_logs_with_previous_and_next(self):
        for index in range(12):
            ActivityLog.objects.create(
                user=self.admin,
                role='Admin',
                action='Login',
                description=f'Audit event {index}',
            )

        first_page = self.client.get(reverse('activity_logs'))
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context['page_obj'].paginator.num_pages, 2)
        self.assertEqual(len(first_page.context['page_obj']), 10)
        self.assertContains(first_page, '?page=2')
        self.assertNotContains(first_page, '?page=0')

        second_page = self.client.get(reverse('activity_logs'), {'page': 2})
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context['page_obj']), 2)
        self.assertContains(second_page, '?page=1')
        self.assertContains(second_page, 'Previous')
        self.assertNotContains(second_page, '>Next</a>')
