from datetime import date

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from activity_logs.models import ActivityLog
from nutrition.models import (
    FollowUpRecord,
    NutritionAssessment,
    classify_nutritional_status,
)
from residents.models import Resident
from dashboard.views import get_dashboard_summary


class NutritionalClassificationTests(SimpleTestCase):
    def test_under_five_classification_uses_who_bmi_for_age(self):
        self.assertEqual(
            classify_nutritional_status(12, 'Female', 48),
            'Underweight'
        )
        self.assertEqual(
            classify_nutritional_status(16, 'Female', 48),
            'Normal'
        )
        self.assertEqual(
            classify_nutritional_status(19, 'Female', 48),
            'Overweight'
        )
        self.assertEqual(
            classify_nutritional_status(22, 'Female', 48),
            'Obese'
        )

    def test_same_bmi_is_classified_by_age_and_sex_reference(self):
        self.assertEqual(
            classify_nutritional_status(20, 'Female', 120),
            'Overweight'
        )
        self.assertEqual(
            classify_nutritional_status(20, 'Female', 240),
            'Normal'
        )

    def test_adult_and_senior_classification_uses_adult_bmi_ranges(self):
        expected_statuses = [
            (17, 'Underweight'),
            (23, 'Normal'),
            (27, 'Overweight'),
            (32, 'Obese'),
        ]

        for bmi, expected_status in expected_statuses:
            with self.subTest(bmi=bmi):
                self.assertEqual(
                    classify_nutritional_status(bmi, 'Male', 720),
                    expected_status
                )


class AssessmentMonitoringTests(TestCase):
    def setUp(self):
        self.resident = Resident.objects.create(
            first_name='Test',
            last_name='Resident',
            sex='Female',
            birth_date=date(2000, 1, 1),
            address='Test Zone',
        )

    def test_non_normal_assessment_stays_in_monitoring_until_normal(self):
        initial_assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 1, 1),
            height=100,
            weight=16,
        )

        followup = FollowUpRecord.objects.get(assessment=initial_assessment)
        self.assertEqual(followup.status, 'Pending')
        self.assertEqual(initial_assessment.monitoring_flag, 'Needs Follow-up')
        followup.status = 'Completed'
        followup.save(update_fields=['status'])
        followup.refresh_from_db()
        self.assertEqual(followup.status, 'Pending')
        self.assertIn('until a Normal assessment', followup.notes)

        followup.status = 'For Referral'
        followup.save(update_fields=['status'])

        normal_assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 2, 1),
            height=100,
            weight=22,
        )

        followup.refresh_from_db()
        self.assertEqual(normal_assessment.nutritional_status, 'Normal')
        self.assertEqual(normal_assessment.monitoring_flag, 'Routine Monitoring')
        self.assertEqual(followup.status, 'Completed')
        self.assertIn('resolved by normal assessment', followup.notes)

    def test_editing_historical_assessment_does_not_reopen_monitoring(self):
        initial_assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 1, 1),
            height=100,
            weight=16,
        )
        followup = FollowUpRecord.objects.get(assessment=initial_assessment)

        NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 2, 1),
            height=100,
            weight=22,
        )
        initial_assessment.weight = 16
        initial_assessment.save()

        followup.refresh_from_db()
        self.assertEqual(followup.status, 'Completed')
        self.assertEqual(FollowUpRecord.objects.filter(status='Pending').count(), 0)

    def test_dashboard_summary_uses_latest_status_per_resident(self):
        NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 1, 1),
            height=100,
            weight=16,
        )
        NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 2, 1),
            height=100,
            weight=22,
        )

        summary = get_dashboard_summary()

        self.assertEqual(summary['underweight'], 0)
        self.assertEqual(summary['normal'], 1)
        self.assertEqual(summary['pending_followups'], 0)
        self.assertEqual(summary['priority_cases'], [])


class StaffArchiveNutritionRecordTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='nutritionarchivestaff',
            password='test-password',
        )
        self.resident = Resident.objects.create(
            first_name='Nutrition',
            last_name='Archive',
            sex='Female',
            birth_date=date(1990, 1, 1),
            address='Test Zone',
        )
        self.client.force_login(self.staff)

    def test_archiving_assessment_preserves_assessment_and_hides_followups(self):
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 10, 20),
            height=160,
            weight=40,
        )
        followup = FollowUpRecord.objects.get(assessment=assessment)

        response = self.client.post(
            reverse('delete_assessment', args=[assessment.pk])
        )

        self.assertRedirects(response, reverse('assessment_list'))
        assessment.refresh_from_db()
        self.assertIsNotNone(assessment.archived_at)
        self.assertFalse(NutritionAssessment.objects.filter(pk=assessment.pk).exists())
        self.assertFalse(FollowUpRecord.objects.filter(pk=followup.pk).exists())
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())

    def test_staff_can_permanently_delete_assessment_and_followups(self):
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 10, 20),
            height=160,
            weight=40,
        )
        followup = FollowUpRecord.objects.get(assessment=assessment)

        response = self.client.post(
            reverse('delete_assessment', args=[assessment.pk]),
            {'action': 'delete'},
        )

        self.assertRedirects(response, reverse('assessment_list'))
        self.assertFalse(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertFalse(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())

    def test_archiving_followup_preserves_record_and_logs_action(self):
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 10, 20),
            height=160,
            weight=59,
        )
        followup = FollowUpRecord.objects.create(
            assessment=assessment,
            follow_up_date=date(2026, 10, 21),
        )

        response = self.client.post(
            reverse('delete_followup', args=[followup.pk])
        )

        self.assertRedirects(response, reverse('followup_list'))
        followup.refresh_from_db()
        self.assertIsNotNone(followup.archived_at)
        self.assertFalse(FollowUpRecord.objects.filter(pk=followup.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
        self.assertTrue(
            ActivityLog.objects.filter(
                action='Archive Record',
                description__contains='Archived follow-up record',
            ).exists()
        )


class AdminReadOnlyNutritionAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            username='adminnutritionviewer',
            password='adminpass123',
            is_staff=True,
            is_superuser=True,
        )

    def test_admin_cannot_open_add_assessment_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('add_assessment'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('assessment_list'))

    def test_admin_cannot_open_add_followup_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('add_followup'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('assessment_list'))

    def test_admin_can_view_dashboard_analytics_logs_assessments_and_add_users(self):
        self.client.force_login(self.admin)

        allowed_urls = [
            reverse('admin_dashboard'),
            reverse('analytics'),
            reverse('report_dashboard'),
            reverse('monthly_report'),
            reverse('annual_report'),
            reverse('export_pdf'),
            reverse('export_excel'),
            reverse('activity_logs'),
            reverse('assessment_list'),
            reverse('add_user'),
            reverse('resident_list'),
            reverse('followup_list'),
        ]

        for url in allowed_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

        dashboard_response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(dashboard_response, 'Logout')

    def test_admin_can_view_read_only_record_lists(self):
        self.client.force_login(self.admin)

        allowed_urls = [
            reverse('resident_list'),
            reverse('followup_list'),
        ]

        for url in allowed_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_admin_is_redirected_from_staff_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('assessment_list'))
