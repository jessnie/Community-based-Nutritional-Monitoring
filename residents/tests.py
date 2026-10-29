from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nutrition.models import FollowUpRecord, NutritionAssessment
from residents.models import Resident


class AdminReadOnlyAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            username='adminviewer',
            password='adminpass123',
            is_staff=True,
            is_superuser=True,
        )

    def test_admin_cannot_open_add_resident_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('add_resident'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('assessment_list'))

    def test_admin_cannot_open_edit_resident_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('edit_resident', args=[1]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('assessment_list'))

    def test_admin_can_archive_or_delete_resident_from_list(self):
        resident = Resident.objects.create(
            first_name='Admin',
            last_name='Resident',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('resident_list'))

        self.assertEqual(response.status_code, 200)
        delete_url = reverse('delete_resident', args=[resident.pk])
        self.assertContains(response, f'{delete_url}?action=archive')
        self.assertContains(response, f'{delete_url}?action=delete')

    def test_admin_can_permanently_delete_resident(self):
        resident = Resident.objects.create(
            first_name='Admin',
            last_name='Delete',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('delete_resident', args=[resident.pk]),
            {'action': 'delete'},
        )

        self.assertRedirects(response, reverse('resident_list'))
        self.assertFalse(Resident.all_objects.filter(pk=resident.pk).exists())


class StaffArchiveResidentTests(TestCase):
    def test_archiving_resident_hides_but_preserves_related_records(self):
        staff = get_user_model().objects.create_user(
            username='archivestaff',
            password='test-password',
        )
        resident = Resident.objects.create(
            first_name='Archived',
            last_name='Resident',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )
        assessment = NutritionAssessment.objects.create(
            resident=resident,
            assessment_date=date(2026, 10, 20),
            height=150,
            weight=25,
        )
        followup = FollowUpRecord.objects.get(assessment=assessment)
        self.client.force_login(staff)

        response = self.client.post(
            reverse('delete_resident', args=[resident.pk])
        )

        self.assertRedirects(response, reverse('resident_list'))
        resident.refresh_from_db()
        self.assertIsNotNone(resident.archived_at)
        self.assertFalse(Resident.objects.filter(pk=resident.pk).exists())
        self.assertFalse(NutritionAssessment.objects.filter(pk=assessment.pk).exists())
        self.assertFalse(FollowUpRecord.objects.filter(pk=followup.pk).exists())
        self.assertTrue(Resident.all_objects.filter(pk=resident.pk).exists())
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())

    def test_staff_can_permanently_delete_resident_and_related_records(self):
        staff = get_user_model().objects.create_user(
            username='permanentdeletestaff',
            password='test-password',
        )
        resident = Resident.objects.create(
            first_name='Deleted',
            last_name='Resident',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )
        assessment = NutritionAssessment.objects.create(
            resident=resident,
            assessment_date=date(2026, 10, 20),
            height=150,
            weight=25,
        )
        followup = FollowUpRecord.objects.get(assessment=assessment)
        self.client.force_login(staff)

        response = self.client.post(
            reverse('delete_resident', args=[resident.pk]),
            {'action': 'delete'},
        )

        self.assertRedirects(response, reverse('resident_list'))
        self.assertFalse(Resident.all_objects.filter(pk=resident.pk).exists())
        self.assertFalse(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertFalse(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
