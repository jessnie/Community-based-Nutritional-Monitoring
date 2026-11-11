from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nutrition.models import FollowUpRecord, NutritionAssessment
from residents.models import Resident
from .models import AdminArchivedRecord, RoleDeletedRecord, StaffArchivedRecord


class StaffArchivedRecordsPageTests(TestCase):
	def setUp(self):
		self.staff = get_user_model().objects.create_user(
			username='staffarchivepage',
			password='test-password',
		)
		self.resident = Resident.objects.create(
			first_name='StaffHidden',
			last_name='Resident',
			sex='Female',
			birth_date=date(2010, 1, 1),
			address='Test Zone',
		)
		self.marker = StaffArchivedRecord.objects.create(
			record_type='resident',
			record_id=self.resident.pk,
			archived_by=self.staff,
		)
		self.client.force_login(self.staff)

	def test_staff_can_restore_record_from_staff_archive(self):
		response = self.client.get(reverse('staff_archived_records'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.resident.resident_id)
		self.assertContains(response, 'value="delete"')

		response = self.client.post(reverse('staff_archived_records'), {
			'record_type': 'resident',
			'record_id': self.resident.pk,
			'action': 'restore',
		})

		self.assertRedirects(response, reverse('staff_archived_records'))
		self.assertFalse(StaffArchivedRecord.objects.filter(pk=self.marker.pk).exists())
		self.assertTrue(Resident.objects.filter(pk=self.resident.pk).exists())

	def test_staff_archived_records_are_paginated(self):
		for index in range(10):
			resident = Resident.objects.create(
				first_name=f'Archived{index}',
				last_name='Resident',
				sex='Female',
				birth_date=date(2010, 1, 1),
				address='Test Zone',
			)
			StaffArchivedRecord.objects.create(
				record_type='resident',
				record_id=resident.pk,
				archived_by=self.staff,
			)

		response = self.client.get(
			reverse('staff_archived_records'),
			{'page': 2},
		)

		self.assertEqual(response.context['page_obj'].number, 2)
		self.assertEqual(len(response.context['page_obj']), 5)
		self.assertContains(response, 'Previous')

	def test_staff_can_permanently_delete_archived_resident_without_affecting_admin(self):
		assessment = NutritionAssessment.objects.create(
			resident=self.resident,
			assessment_date=date(2026, 10, 20),
			height=150,
			weight=25,
		)
		followup = FollowUpRecord.objects.get(assessment=assessment)
		assessment_marker = StaffArchivedRecord.objects.create(
			record_type='assessment',
			record_id=assessment.pk,
			archived_by=self.staff,
		)
		followup_marker = StaffArchivedRecord.objects.create(
			record_type='followup',
			record_id=followup.pk,
			archived_by=self.staff,
		)
		response = self.client.post(reverse('staff_archived_records'), {
			'record_type': 'resident',
			'record_id': self.resident.pk,
			'action': 'delete',
		})

		self.assertRedirects(response, reverse('staff_archived_records'))
		self.assertTrue(Resident.all_objects.filter(pk=self.resident.pk).exists())
		self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
		self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
		self.assertFalse(StaffArchivedRecord.objects.filter(
			pk__in=[self.marker.pk, assessment_marker.pk, followup_marker.pk],
		).exists())
		self.assertTrue(RoleDeletedRecord.objects.filter(
			role='staff',
			record_type='resident',
			record_id=self.resident.pk,
		).exists())
		self.assertFalse(AdminArchivedRecord.objects.filter(
			record_type='resident',
			record_id=self.resident.pk,
		).exists())

		admin = get_user_model().objects.create_superuser(
			username='staffdeletefromarchiveadmin',
			password='test-password',
		)
		self.client.force_login(admin)
		self.assertContains(self.client.get(reverse('resident_list')), self.resident.first_name)
		self.assertIn(
			assessment,
			self.client.get(reverse('assessment_list')).context['assessments'],
		)
		self.assertIn(
			followup,
			self.client.get(reverse('followup_list')).context['followups'],
		)

	def test_staff_can_permanently_delete_archived_assessment(self):
		assessment = NutritionAssessment.objects.create(
			resident=self.resident,
			assessment_date=date(2026, 10, 21),
			height=150,
			weight=25,
		)
		followup = FollowUpRecord.objects.get(assessment=assessment)
		StaffArchivedRecord.objects.create(
			record_type='assessment',
			record_id=assessment.pk,
			archived_by=self.staff,
		)
		StaffArchivedRecord.objects.create(
			record_type='followup',
			record_id=followup.pk,
			archived_by=self.staff,
		)

		response = self.client.post(reverse('staff_archived_records'), {
			'record_type': 'assessment',
			'record_id': assessment.pk,
			'action': 'delete',
		})

		self.assertRedirects(response, reverse('staff_archived_records'))
		self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
		self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
		self.assertTrue(RoleDeletedRecord.objects.filter(
			role='staff', record_type='assessment', record_id=assessment.pk,
		).exists())
		self.assertFalse(StaffArchivedRecord.objects.filter(
			record_type='followup', record_id=followup.pk,
		).exists())

		admin = get_user_model().objects.create_superuser(
			username='staffassessmentdeleteadmin',
			password='test-password',
		)
		self.client.force_login(admin)
		self.assertIn(
			assessment,
			self.client.get(reverse('assessment_list')).context['assessments'],
		)
		self.assertIn(
			followup,
			self.client.get(reverse('followup_list')).context['followups'],
		)

	def test_staff_can_permanently_delete_archived_followup(self):
		assessment = NutritionAssessment.objects.create(
			resident=self.resident,
			assessment_date=date(2026, 10, 22),
			height=150,
			weight=59,
		)
		followup = FollowUpRecord.objects.create(
			assessment=assessment,
			follow_up_date=date(2026, 10, 23),
		)
		StaffArchivedRecord.objects.create(
			record_type='followup',
			record_id=followup.pk,
			archived_by=self.staff,
		)

		response = self.client.post(reverse('staff_archived_records'), {
			'record_type': 'followup',
			'record_id': followup.pk,
			'action': 'delete',
		})

		self.assertRedirects(response, reverse('staff_archived_records'))
		self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
		self.assertTrue(RoleDeletedRecord.objects.filter(
			role='staff', record_type='followup', record_id=followup.pk,
		).exists())

		admin = get_user_model().objects.create_superuser(
			username='stafffollowupdeleteadmin',
			password='test-password',
		)
		self.client.force_login(admin)
		self.assertIn(
			followup,
			self.client.get(reverse('followup_list')).context['followups'],
		)

	def test_admin_cannot_open_staff_archive(self):
		admin = get_user_model().objects.create_superuser(
			username='staffarchiveadmin',
			password='test-password',
		)
		self.client.force_login(admin)

		response = self.client.get(reverse('staff_archived_records'))

		self.assertRedirects(response, reverse('admin_dashboard'))
