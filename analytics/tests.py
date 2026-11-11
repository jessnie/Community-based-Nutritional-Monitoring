from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nutrition.models import NutritionAssessment
from residents.models import Resident


class LiveAnalyticsStatsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='analytics-staff',
            password='test-password',
        )
        self.client.force_login(self.user)

    def test_live_endpoint_returns_current_analytics(self):
        url = reverse('live_analytics_stats')

        initial_response = self.client.get(url)
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(initial_response.json()['total_residents'], 0)

        Resident.objects.create(
            first_name='Analytics',
            last_name='Resident',
            sex='Female',
            birth_date=date(1990, 1, 1),
            address='Test Zone',
        )

        updated_response = self.client.get(url)
        self.assertEqual(updated_response.status_code, 200)
        self.assertEqual(updated_response.json()['total_residents'], 1)

    def test_live_endpoint_requires_authentication(self):
        self.client.logout()

        response = self.client.get(reverse('live_analytics_stats'))

        self.assertEqual(response.status_code, 302)

    def test_current_status_counts_latest_assessment_while_history_keeps_all(self):
        resident = Resident.objects.create(
            first_name='Status',
            last_name='History',
            sex='Female',
            birth_date=date(1990, 1, 1),
            address='Test Zone',
        )
        NutritionAssessment.objects.create(
            resident=resident,
            assessment_date=date(2026, 1, 15),
            height=170,
            weight=49,
        )
        NutritionAssessment.objects.create(
            resident=resident,
            assessment_date=date(2026, 2, 15),
            height=170,
            weight=65,
        )

        data = self.client.get(reverse('live_analytics_stats')).json()

        self.assertEqual(data['total_assessments'], 2)
        self.assertEqual(data['assessed_residents'], 1)
        self.assertEqual(data['status_chart_data'], [1, 0, 0, 0])
        self.assertEqual(data['normal'], 1)
        self.assertEqual(data['underweight'], 0)
        self.assertEqual(data['routine_monitoring'], 1)
        self.assertEqual(data['needs_followup'], 0)
        self.assertEqual(data['months'], ['Jan 2026', 'Feb 2026'])
        self.assertEqual(data['monthly_counts'], [1, 1])
        self.assertEqual(data['monthly_needs_followup'], [1, 0])

    def test_staff_analytics_page_renders_live_refresh_status(self):
        response = self.client.get(reverse('analytics'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'analytics-last-updated')
        self.assertContains(response, reverse('live_analytics_stats'))

    def test_admin_analytics_page_renders_live_refresh_status(self):
        admin = get_user_model().objects.create_superuser(
            username='analytics-admin',
            email='analytics-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('analytics'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'analytics-last-updated')
        self.assertContains(response, reverse('live_analytics_stats'))
