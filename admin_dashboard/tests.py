from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from activity_logs.models import (
    ActivityLog,
    AdminArchivedRecord,
    RoleDeletedRecord,
)
from nutrition.models import NutritionAssessment
from residents.models import Resident


class UnassessedResidentDashboardTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='unassessedadmin',
            email='unassessedadmin@example.com',
            password='test-password',
        )
        self.staff = get_user_model().objects.create_user(
            username='unassessedstaff',
            password='test-password',
        )

    def create_resident(self, first_name):
        return Resident.objects.create(
            first_name=first_name,
            last_name='Resident',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )

    def test_dashboard_counts_and_links_residents_without_visible_assessment(self):
        unassessed = self.create_resident('Unassessed')
        assessed = self.create_resident('Assessed')
        hidden_assessment_resident = self.create_resident('HiddenAssessment')
        hidden_resident = self.create_resident('HiddenResident')
        NutritionAssessment.objects.create(
            resident=assessed,
            assessment_date=date.today(),
            height=120,
            weight=22,
        )
        hidden_assessment = NutritionAssessment.objects.create(
            resident=hidden_assessment_resident,
            assessment_date=date.today(),
            height=120,
            weight=22,
        )
        AdminArchivedRecord.objects.create(
            record_type='assessment',
            record_id=hidden_assessment.pk,
            archived_by=self.admin,
        )
        AdminArchivedRecord.objects.create(
            record_type='resident',
            record_id=hidden_resident.pk,
            archived_by=self.admin,
        )

        self.client.force_login(self.admin)
        dashboard = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(dashboard.context['residents_without_assessment'], 2)
        self.assertContains(dashboard, reverse('unassessed_residents'))

        page = self.client.get(reverse('unassessed_residents'))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, unassessed.first_name)
        self.assertContains(page, hidden_assessment_resident.first_name)
        self.assertNotContains(page, assessed.first_name)
        self.assertNotContains(page, hidden_resident.first_name)

    def test_staff_cannot_open_unassessed_resident_list(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('unassessed_residents'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            f'{reverse("login")}?next={reverse("unassessed_residents")}',
        )


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

    def test_admin_archived_records_are_paginated(self):
        for index in range(10):
            resident = Resident.objects.create(
                first_name=f'Archived{index}',
                last_name='Resident',
                sex='Female',
                birth_date=date(2010, 1, 1),
                address='Test Zone',
            )
            AdminArchivedRecord.objects.create(
                record_type='resident',
                record_id=resident.pk,
                archived_by=self.admin,
            )

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('archived_records'),
            {'page': 2},
        )

        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['page_obj']), 5)
        self.assertContains(response, 'Previous')

    def test_admin_can_permanently_delete_from_admin_records_only(self):
        resident = Resident.objects.create(
            first_name='Shared',
            last_name='Record',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )
        AdminArchivedRecord.objects.create(
            record_type='resident',
            record_id=resident.pk,
            archived_by=self.admin,
        )
        self.client.force_login(self.admin)

        response = self.client.post(reverse('archived_records'), {
            'record_type': 'resident',
            'record_id': resident.pk,
            'action': 'delete',
        })

        self.assertRedirects(response, reverse('archived_records'))
        self.assertTrue(Resident.all_objects.filter(pk=resident.pk).exists())
        self.assertFalse(AdminArchivedRecord.objects.filter(
            record_type='resident',
            record_id=resident.pk,
        ).exists())
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='admin',
            record_type='resident',
            record_id=resident.pk,
        ).exists())

        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse('resident_list')), resident.first_name)


class RoleSpecificAdminArchiveTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='rolearchiveadmin',
            password='test-password',
        )
        self.staff = get_user_model().objects.create_user(
            username='rolearchivestaff',
            password='test-password',
        )
        self.resident = Resident.objects.create(
            first_name='AdminOnlyHidden',
            last_name='Resident',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )

    def test_admin_archive_and_restore_do_not_change_staff_visibility(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('delete_resident', args=[self.resident.pk]),
            {'action': 'archive'},
        )

        self.assertRedirects(response, reverse('resident_list'))
        self.assertTrue(AdminArchivedRecord.objects.filter(
            record_type='resident',
            record_id=self.resident.pk,
        ).exists())
        admin_list = self.client.get(reverse('resident_list'))
        self.assertNotContains(admin_list, 'AdminOnlyHidden')
        self.assertContains(
            self.client.get(reverse('archived_records')),
            'AdminOnlyHidden',
        )

        self.client.force_login(self.staff)
        self.assertContains(
            self.client.get(reverse('resident_list')),
            'AdminOnlyHidden',
        )
        self.assertNotContains(
            self.client.get(reverse('staff_archived_records')),
            'AdminOnlyHidden',
        )

        self.client.force_login(self.admin)
        response = self.client.post(reverse('archived_records'), {
            'record_type': 'resident',
            'record_id': self.resident.pk,
            'action': 'restore',
        })

        self.assertRedirects(response, reverse('archived_records'))
        self.assertFalse(AdminArchivedRecord.objects.filter(
            record_type='resident',
            record_id=self.resident.pk,
        ).exists())
        self.assertContains(self.client.get(reverse('resident_list')), 'AdminOnlyHidden')


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
