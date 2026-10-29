from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nutrition.models import FollowUpRecord, NutritionAssessment
from residents.models import Resident


class StaffNutritionResourcesTests(TestCase):
	def test_staff_dashboard_displays_official_printable_resources(self):
		staff_user = get_user_model().objects.create_user(
			username='nutritionstaff',
			password='test-password',
		)
		self.client.force_login(staff_user)

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Nutrition Education Resources')
		self.assertContains(response, 'PP-Pinoy.png')
		self.assertContains(response, 'complementary-feeding.tmb-1024v.jpg')
		self.assertContains(response, 'View / Download Kids PDF')
		self.assertContains(response, 'View / Download Teens PDF')
		self.assertContains(response, 'View / Download Adults PDF')
		self.assertContains(response, 'View / Download Older Adults PDF')
		self.assertContains(response, 'Infant and Young Child Feeding')
		self.assertContains(response, 'View / Download WHO Handouts')
		self.assertContains(response, 'Physical Activity Resources')
		self.assertContains(response, 'physical-activity.tmb-1920v.jpg')
		self.assertContains(response, 'View / Download Infographic')


class DashboardAnalyticsChartTests(TestCase):
	def test_staff_dashboard_renders_both_chart_panels(self):
		user = get_user_model().objects.create_user(
			username='chartstaff',
			password='test-password',
		)
		self.client.force_login(user)

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Nutrition Status Distribution')
		self.assertContains(response, 'Monthly Assessment Trend')
		self.assertContains(response, 'dashboard-status-chart')
		self.assertContains(response, 'dashboard-trend-chart')

	def test_dashboard_shows_recent_assessments_and_followups(self):
		user = get_user_model().objects.create_user(
			username='activitystaff',
			password='test-password',
		)
		resident = Resident.objects.create(
			first_name='Recent',
			last_name='Resident',
			sex='Female',
			birth_date=date(1990, 1, 1),
			address='Test Zone',
		)
		assessment = NutritionAssessment.objects.create(
			resident=resident,
			assessment_date=date(2026, 10, 20),
			height=160,
			weight=70,
		)
		FollowUpRecord.objects.create(
			assessment=assessment,
			follow_up_date=date(2026, 10, 21),
			status='Pending',
		)
		self.client.force_login(user)

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Recent Activity')
		self.assertContains(response, 'Recent Assessments')
		self.assertContains(response, 'Recent Follow-ups')
		self.assertContains(response, 'Recent Resident')
		self.assertContains(response, reverse('assessment_list'))
		self.assertContains(response, reverse('followup_list'))

	@patch('dashboard.views.timezone.localdate', return_value=date(2026, 10, 21))
	def test_live_dashboard_returns_chart_data_for_status_and_recent_trend(self, _localdate):
		user = get_user_model().objects.create_user(
			username='chartstaff',
			password='test-password',
		)
		resident = Resident.objects.create(
			first_name='Chart',
			last_name='Resident',
			sex='Female',
			birth_date=date(1990, 1, 1),
			address='Test Zone',
		)
		for assessment_date, weight in (
			(date(2026, 9, 10), 70),
			(date(2026, 9, 20), 72),
			(date(2026, 10, 10), 75),
		):
			NutritionAssessment.objects.create(
				resident=resident,
				assessment_date=assessment_date,
				height=160,
				weight=weight,
			)

		self.client.force_login(user)
		response = self.client.get(reverse('live_dashboard_stats'))

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(len(data['nutrition_status_chart_data']), 4)
		self.assertEqual(sum(data['nutrition_status_chart_data']), 1)
		self.assertEqual(data['assessment_trend_labels'][0], 'Nov 2025')
		self.assertEqual(data['assessment_trend_labels'][-1], 'Oct 2026')
		self.assertEqual(data['assessment_trend_counts'][-2:], [2, 1])
