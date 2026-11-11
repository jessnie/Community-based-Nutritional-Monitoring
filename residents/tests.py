from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nutrition.models import FollowUpRecord, NutritionAssessment
from residents.models import Resident
from activity_logs.models import (
    AdminArchivedRecord,
    RoleDeletedRecord,
    StaffArchivedRecord,
)


class ResidentClassificationListTests(TestCase):
    def setUp(self):
        today = date.today()
        self.staff = get_user_model().objects.create_user(
            username='classificationstaff',
            password='test-password',
        )
        self.residents = {}
        for name, age in [('Kid', 8), ('Teen', 15), ('Adult', 30), ('Senior', 65)]:
            year = today.year - age
            try:
                birth_date = today.replace(year=year)
            except ValueError:
                birth_date = today.replace(year=year, day=28)
            self.residents[name] = Resident.objects.create(
                first_name=name,
                last_name='Resident',
                sex='Female',
                birth_date=birth_date,
                address='Test Zone',
            )
        self.client.force_login(self.staff)

    def test_resident_list_filters_by_classification(self):
        for classification, expected_name in [
            ('kids', 'Kid'),
            ('teens', 'Teen'),
            ('adults', 'Adult'),
            ('senior', 'Senior'),
        ]:
            with self.subTest(classification=classification):
                response = self.client.get(
                    reverse('resident_list'),
                    {'classification': classification},
                )

                self.assertEqual(response.status_code, 200)
                names = [
                    resident.first_name
                    for resident in response.context['page_obj'].object_list
                ]
                self.assertEqual(names, [expected_name])

    def test_resident_list_combines_classification_and_text_search(self):
        response = self.client.get(
            reverse('resident_list'),
            {'classification': 'teens', 'search': 'Teen'},
        )

        names = [
            resident.first_name
            for resident in response.context['page_obj'].object_list
        ]
        self.assertEqual(names, ['Teen'])
        self.assertEqual(response.context['classification'], 'teens')

    def test_staff_can_view_resident_profile_in_modal(self):
        resident = self.residents['Adult']

        response = self.client.get(
            reverse('view_resident', args=[resident.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'residents/_resident_profile.html')
        self.assertContains(response, resident.resident_id)
        self.assertContains(response, 'Nutrition Assessment')

    def test_staff_resident_actions_can_open_and_submit_in_modals(self):
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        create_url = reverse('add_resident')

        create_form = self.client.get(create_url, **ajax_headers)
        self.assertEqual(create_form.status_code, 200)
        self.assertTemplateUsed(
            create_form,
            'residents/_resident_form_fields.html',
        )

        create_response = self.client.post(
            create_url,
            {
                'first_name': 'Modal',
                'middle_name': '',
                'last_name': 'Resident',
                'sex': 'Female',
                'birth_date': '2010-01-01',
                'address': 'Test Zone',
                'contact_number': '',
                'guardian_name': '',
            },
            **ajax_headers,
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertJSONEqual(create_response.content, {'success': True})
        resident = Resident.objects.get(first_name='Modal')
        self.assertEqual(resident.created_by, self.staff)

        edit_url = reverse('edit_resident', args=[resident.pk])
        edit_form = self.client.get(edit_url, **ajax_headers)
        self.assertEqual(edit_form.status_code, 200)
        self.assertTemplateUsed(
            edit_form,
            'residents/_resident_form_fields.html',
        )
        self.assertContains(edit_form, 'Update')

        edit_response = self.client.post(
            edit_url,
            {
                'first_name': 'Updated',
                'middle_name': '',
                'last_name': 'Resident',
                'sex': 'Female',
                'birth_date': '2010-01-01',
                'address': 'Updated Zone',
                'contact_number': '',
                'guardian_name': '',
            },
            **ajax_headers,
        )
        self.assertEqual(edit_response.status_code, 200)
        self.assertJSONEqual(edit_response.content, {
            'success': True,
            'message': 'Update successfully',
        })
        resident.refresh_from_db()
        self.assertEqual(resident.first_name, 'Updated')

    def test_staff_resident_archive_and_delete_confirmations_use_modals(self):
        resident = self.residents['Adult']
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        for action in ('archive', 'delete'):
            with self.subTest(action=action):
                response = self.client.get(
                    reverse('delete_resident', args=[resident.pk]),
                    {'action': action},
                    **ajax_headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response,
                    'residents/_resident_delete_confirmation.html',
                )
                self.assertContains(
                    response,
                    f'action="{reverse("delete_resident", args=[resident.pk])}?action={action}"',
                )

        archive_response = self.client.post(
            reverse('delete_resident', args=[resident.pk]),
            {'action': 'archive'},
            **ajax_headers,
        )
        self.assertEqual(archive_response.status_code, 200)
        self.assertJSONEqual(archive_response.content, {'success': True})
        self.assertTrue(StaffArchivedRecord.objects.filter(
            record_type='resident',
            record_id=resident.pk,
        ).exists())

        delete_resident = self.residents['Teen']
        delete_response = self.client.post(
            reverse('delete_resident', args=[delete_resident.pk]),
            {'action': 'delete'},
            **ajax_headers,
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertJSONEqual(delete_response.content, {'success': True})
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='staff',
            record_type='resident',
            record_id=delete_resident.pk,
        ).exists())


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

    def test_admin_resident_archive_confirmation_can_open_as_modal(self):
        resident = Resident.objects.create(
            first_name='Admin',
            last_name='Modal',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('delete_resident', args=[resident.pk]),
            {'action': 'archive'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            'residents/_resident_delete_confirmation.html',
        )

    def test_admin_can_view_resident_profile_in_modal(self):
        resident = Resident.objects.create(
            first_name='Admin',
            last_name='Profile',
            sex='Female',
            birth_date=date(2010, 1, 1),
            address='Test Zone',
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('view_resident', args=[resident.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'residents/_resident_profile.html')
        self.assertContains(response, resident.resident_id)

    def test_admin_delete_hides_resident_and_nutrition_records_from_admin_only(self):
        resident = Resident.objects.create(
            first_name='AdminScoped',
            last_name='Delete',
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
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('delete_resident', args=[resident.pk]),
            {'action': 'delete'},
        )

        self.assertRedirects(response, reverse('resident_list'))
        self.assertTrue(Resident.all_objects.filter(pk=resident.pk).exists())
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
        self.assertFalse(AdminArchivedRecord.objects.filter(
            record_type='resident',
            record_id=resident.pk,
        ).exists())
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='admin',
            record_type='resident',
            record_id=resident.pk,
        ).exists())
        self.assertNotContains(self.client.get(reverse('resident_list')), resident.first_name)

        staff = get_user_model().objects.create_user(
            username='admin-deleted-record-staff',
            password='test-password',
        )
        self.client.force_login(staff)
        self.assertContains(self.client.get(reverse('resident_list')), resident.first_name)
        self.assertIn(
            assessment,
            self.client.get(reverse('assessment_list')).context['assessments'],
        )
        self.assertIn(
            followup,
            self.client.get(reverse('followup_list')).context['followups'],
        )
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
        self.assertIsNone(resident.archived_at)
        self.assertTrue(
            StaffArchivedRecord.objects.filter(
                record_type='resident',
                record_id=resident.pk,
            ).exists()
        )
        self.assertTrue(Resident.objects.filter(pk=resident.pk).exists())
        self.assertTrue(NutritionAssessment.objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.objects.filter(pk=followup.pk).exists())
        self.assertTrue(Resident.all_objects.filter(pk=resident.pk).exists())
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
        resident_list = self.client.get(reverse('resident_list'))
        assessment_list = self.client.get(reverse('assessment_list'))
        followup_list = self.client.get(reverse('followup_list'))
        self.assertNotIn(resident, resident_list.context['page_obj'].object_list)
        self.assertNotIn(assessment, assessment_list.context['assessments'])
        self.assertNotIn(followup, followup_list.context['followups'])

        admin = get_user_model().objects.create_superuser(
            username='archiveadmin',
            password='test-password',
        )
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse('resident_list')), resident.first_name)
        self.assertContains(self.client.get(reverse('assessment_list')), resident.first_name)
        self.assertContains(self.client.get(reverse('followup_list')), resident.first_name)

    def test_staff_delete_request_permanently_removes_resident_from_staff_only(self):
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
        resident.refresh_from_db()
        self.assertFalse(StaffArchivedRecord.objects.filter(
            record_type='resident',
            record_id=resident.pk,
        ).exists())
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='staff',
            record_type='resident',
            record_id=resident.pk,
        ).exists())
        self.assertTrue(Resident.all_objects.filter(pk=resident.pk).exists())
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())

        admin = get_user_model().objects.create_superuser(
            username='staff-delete-admin',
            password='test-password',
        )
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse('resident_list')), resident.first_name)
        self.assertIn(
            assessment,
            self.client.get(reverse('assessment_list')).context['assessments'],
        )
        self.assertIn(
            followup,
            self.client.get(reverse('followup_list')).context['followups'],
        )
