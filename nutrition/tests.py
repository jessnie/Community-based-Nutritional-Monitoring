from datetime import date

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from activity_logs.models import (
    ActivityLog,
    AdminArchivedRecord,
    RoleDeletedRecord,
    StaffArchivedRecord,
)
from nutrition.models import (
    FollowUpRecord,
    NutritionAssessment,
    classify_nutritional_status,
)
from nutrition.forms import NutritionAssessmentForm
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

    def test_assessment_form_rejects_date_before_resident_birth_date(self):
        form = NutritionAssessmentForm(data={
            'resident': self.resident.pk,
            'assessment_date': '1999-12-31',
            'height': '100',
            'weight': '16',
        })

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Assessment date cannot be before the resident's date of birth.",
            form.errors['assessment_date'][0],
        )

    def test_staff_can_edit_assessment_in_a_modal(self):
        staff = get_user_model().objects.create_user(
            username='assessmentmodalstaff',
            password='test-password',
        )
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 1, 1),
            height=100,
            weight=16,
            assessed_by=staff,
        )
        self.client.force_login(staff)
        edit_url = reverse('edit_assessment', args=[assessment.pk])
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        form_response = self.client.get(edit_url, **ajax_headers)
        self.assertEqual(form_response.status_code, 200)
        self.assertTemplateUsed(
            form_response,
            'nutrition/_assessment_form_fields.html',
        )
        self.assertContains(form_response, 'Update')

        update_response = self.client.post(
            edit_url,
            {
                'resident': self.resident.pk,
                'assessment_date': '2026-01-02',
                'height': '100',
                'weight': '17',
            },
            **ajax_headers,
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertJSONEqual(update_response.content, {
            'success': True,
            'message': 'Update successfully',
        })
        assessment.refresh_from_db()
        self.assertEqual(assessment.assessment_date, date(2026, 1, 2))
        self.assertEqual(assessment.weight, 17)

    def test_staff_can_create_assessment_from_assessment_modal(self):
        staff = get_user_model().objects.create_user(
            username='assessmentcreatemodalstaff',
            password='test-password',
        )
        self.client.force_login(staff)
        add_url = reverse('add_assessment')
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        assessment_list_response = self.client.get(reverse('assessment_list'))
        self.assertContains(assessment_list_response, add_url)
        self.assertContains(
            assessment_list_response,
            'data-modal-title="Add Nutrition Assessment"',
        )

        form_response = self.client.get(add_url, **ajax_headers)
        self.assertEqual(form_response.status_code, 200)
        self.assertTemplateUsed(
            form_response,
            'nutrition/_assessment_form_fields.html',
        )

        create_response = self.client.post(
            add_url,
            {
                'resident': self.resident.pk,
                'assessment_date': '2026-01-02',
                'height': '100',
                'weight': '17',
            },
            **ajax_headers,
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertJSONEqual(create_response.content, {'success': True})
        assessment = NutritionAssessment.objects.get(
            resident=self.resident,
            assessment_date=date(2026, 1, 2),
        )
        self.assertEqual(assessment.assessed_by, staff)

    def test_staff_can_create_followup_from_assessment_modal(self):
        staff = get_user_model().objects.create_user(
            username='followupmodalstaff',
            password='test-password',
        )
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 1, 1),
            height=100,
            weight=16,
            assessed_by=staff,
        )
        self.client.force_login(staff)
        add_url = reverse('add_followup')
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        followup_list_response = self.client.get(reverse('followup_list'))
        self.assertContains(followup_list_response, add_url)
        self.assertContains(
            followup_list_response,
            'data-modal-title="Add Follow-Up Record"',
        )

        form_response = self.client.get(
            add_url,
            {'assessment': assessment.pk},
            **ajax_headers,
        )
        self.assertEqual(form_response.status_code, 200)
        self.assertTemplateUsed(
            form_response,
            'nutrition/_followup_form_fields.html',
        )
        self.assertContains(form_response, f'value="{assessment.pk}" selected')

        create_response = self.client.post(
            add_url,
            {
                'assessment': assessment.pk,
                'follow_up_date': '2026-01-02',
                'status': 'Pending',
                'follow_up_method': 'Home Visit',
                'notes': 'Modal follow-up',
                'next_follow_up_date': '',
            },
            **ajax_headers,
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertJSONEqual(create_response.content, {'success': True})
        followup = FollowUpRecord.objects.get(
            assessment=assessment,
            notes='Modal follow-up',
        )
        self.assertEqual(followup.recorded_by, staff)

    def test_follow_up_method_can_record_home_visit(self):
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 1, 1),
            height=100,
            weight=16,
        )
        followup = FollowUpRecord.objects.get(assessment=assessment)

        followup.follow_up_method = 'Home Visit'
        followup.save(update_fields=['follow_up_method'])

        followup.refresh_from_db()
        self.assertEqual(followup.follow_up_method, 'Home Visit')

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
        self.assertIsNone(assessment.archived_at)
        self.assertTrue(
            StaffArchivedRecord.objects.filter(
                record_type='assessment',
                record_id=assessment.pk,
            ).exists()
        )
        self.assertTrue(NutritionAssessment.objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.objects.filter(pk=followup.pk).exists())
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
        self.assertNotIn(
            assessment,
            self.client.get(reverse('assessment_list')).context['assessments'],
        )
        self.assertEqual(
            list(self.client.get(reverse('followup_list')).context['followups']),
            [],
        )

        admin = get_user_model().objects.create_superuser(
            username='nutritionarchiveadmin',
            password='test-password',
        )
        self.client.force_login(admin)
        admin_assessment_list = self.client.get(reverse('assessment_list'))
        self.assertIn(
            assessment,
            admin_assessment_list.context['assessments'],
        )
        admin_followup_list = self.client.get(reverse('followup_list'))
        self.assertIn(
            followup,
            admin_followup_list.context['followups'],
        )

    def test_staff_archive_and_delete_confirmations_use_modals(self):
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 10, 20),
            height=160,
            weight=40,
        )
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        delete_url = reverse('delete_assessment', args=[assessment.pk])

        for action in ('archive', 'delete'):
            with self.subTest(action=action):
                response = self.client.get(
                    delete_url,
                    {'action': action},
                    **ajax_headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response,
                    'nutrition/_assessment_delete_confirmation.html',
                )
                self.assertContains(response, f'value="{action}"')
                self.assertContains(response, action.title())

        response = self.client.post(
            delete_url,
            {'action': 'archive'},
            **ajax_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True})
        self.assertTrue(StaffArchivedRecord.objects.filter(
            record_type='assessment',
            record_id=assessment.pk,
        ).exists())

    def test_staff_delete_permanently_removes_assessment_from_staff_only(self):
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
        assessment.refresh_from_db()
        self.assertFalse(StaffArchivedRecord.objects.filter(
            record_type='assessment',
            record_id=assessment.pk,
        ).exists())
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='staff',
            record_type='assessment',
            record_id=assessment.pk,
        ).exists())
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())

    def test_staff_delete_permanently_removes_followup_from_staff_only(self):
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
            reverse('delete_followup', args=[followup.pk]),
            {'action': 'delete'},
        )

        self.assertRedirects(response, reverse('followup_list'))
        followup.refresh_from_db()
        self.assertIsNone(followup.archived_at)
        self.assertFalse(StaffArchivedRecord.objects.filter(
            record_type='followup',
            record_id=followup.pk,
        ).exists())
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='staff',
            record_type='followup',
            record_id=followup.pk,
        ).exists())
        self.assertTrue(FollowUpRecord.objects.filter(pk=followup.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=followup.pk).exists())
        self.assertTrue(
            ActivityLog.objects.filter(
                action='Permanently Delete Record',
                description__contains='from staff records',
            ).exists()
        )

        admin = get_user_model().objects.create_superuser(
            username='followupadmin',
            password='test-password',
        )
        self.client.force_login(admin)
        admin_response = self.client.get(reverse('followup_list'))
        self.assertIn(followup, admin_response.context['followups'])

    def test_staff_can_edit_followup_in_followup_monitoring_modal(self):
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 10, 20),
            height=160,
            weight=40,
        )
        followup = FollowUpRecord.objects.create(
            assessment=assessment,
            follow_up_date=date(2026, 10, 21),
            notes='Before update',
        )
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        edit_url = reverse('edit_followup', args=[followup.pk])

        list_response = self.client.get(reverse('followup_list'))
        self.assertContains(list_response, edit_url)
        self.assertContains(list_response, 'data-modal-title="Edit Follow-Up"')

        form_response = self.client.get(edit_url, **ajax_headers)
        self.assertEqual(form_response.status_code, 200)
        self.assertTemplateUsed(
            form_response,
            'nutrition/_followup_form_fields.html',
        )
        self.assertContains(form_response, 'Update')

        update_response = self.client.post(
            edit_url,
            {
                'assessment': assessment.pk,
                'follow_up_date': '2026-10-22',
                'status': 'Pending',
                'follow_up_method': 'Home Visit',
                'notes': 'Updated in modal',
                'next_follow_up_date': '',
            },
            **ajax_headers,
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertJSONEqual(update_response.content, {
            'success': True,
            'message': 'Update successfully',
        })
        followup.refresh_from_db()
        self.assertEqual(followup.notes, 'Updated in modal')

    def test_staff_followup_archive_and_delete_confirmations_use_modals(self):
        assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 10, 20),
            height=160,
            weight=40,
        )
        followup = FollowUpRecord.objects.create(
            assessment=assessment,
            follow_up_date=date(2026, 10, 21),
        )
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        delete_url = reverse('delete_followup', args=[followup.pk])

        for action in ('archive', 'delete'):
            with self.subTest(action=action):
                response = self.client.get(
                    delete_url,
                    {'action': action},
                    **ajax_headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response,
                    'nutrition/_followup_delete_confirmation.html',
                )
                self.assertContains(response, f'value="{action}"')
                self.assertContains(response, action.title())

        archive_response = self.client.post(
            delete_url,
            {'action': 'archive'},
            **ajax_headers,
        )
        self.assertEqual(archive_response.status_code, 200)
        self.assertJSONEqual(archive_response.content, {'success': True})
        self.assertTrue(StaffArchivedRecord.objects.filter(
            record_type='followup',
            record_id=followup.pk,
        ).exists())

    def test_assessment_and_followup_lists_are_paginated(self):
        for day in range(1, 12):
            resident = Resident.objects.create(
                first_name=f'Nutrition{day}',
                last_name='Pagination',
                sex='Female',
                birth_date=date(1990, 1, 1),
                address='Test Zone',
            )
            assessment = NutritionAssessment.objects.create(
                resident=resident,
                assessment_date=date(2026, 11, day),
                height=160,
                weight=60,
            )
            FollowUpRecord.objects.create(
                assessment=assessment,
                follow_up_date=date(2026, 11, day),
                status='Completed',
            )

        assessment_response = self.client.get(
            reverse('assessment_list'),
            {'page': 2},
        )
        self.assertEqual(assessment_response.context['page_obj'].number, 2)
        self.assertEqual(len(assessment_response.context['page_obj']), 5)
        self.assertContains(assessment_response, 'Previous')
        first_assessment_page = self.client.get(reverse('assessment_list'))
        self.assertContains(first_assessment_page, 'Page 1 of 3')
        self.assertContains(first_assessment_page, 'Next')

        followup_response = self.client.get(
            reverse('followup_list'),
            {'page': 2, 'search': 'Nutrition', 'status': 'Completed'},
        )
        self.assertEqual(followup_response.context['page_obj'].number, 2)
        self.assertTrue(followup_response.context['page_obj'].has_previous())
        self.assertEqual(len(followup_response.context['page_obj']), 5)
        self.assertContains(followup_response, 'search=Nutrition')
        self.assertContains(followup_response, 'status=Completed')
        first_followup_page = self.client.get(
            reverse('followup_list'),
            {'search': 'Nutrition', 'status': 'Completed'},
        )
        self.assertContains(first_followup_page, 'Next')

        admin = get_user_model().objects.create_superuser(
            username='nutritionpaginationadmin',
            password='test-password',
        )
        self.client.force_login(admin)
        admin_assessment_response = self.client.get(
            reverse('assessment_list'),
            {'page': 2},
        )
        self.assertContains(admin_assessment_response, 'Page 2 of 3')
        admin_followup_response = self.client.get(
            reverse('followup_list'),
            {'page': 2, 'search': 'Nutrition', 'status': 'Completed'},
        )
        self.assertContains(admin_followup_response, 'Page 2 of 3')


class RoleSpecificNutritionArchiveTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='nutritionroleadmin',
            password='test-password',
        )
        self.staff = get_user_model().objects.create_user(
            username='nutritionrolestaff',
            password='test-password',
        )
        self.resident = Resident.objects.create(
            first_name='RoleSpecific',
            last_name='Resident',
            sex='Female',
            birth_date=date(1990, 1, 1),
            address='Test Zone',
        )
        self.assessment = NutritionAssessment.objects.create(
            resident=self.resident,
            assessment_date=date(2026, 10, 20),
            height=160,
            weight=40,
        )
        self.followup = FollowUpRecord.objects.get(
            assessment=self.assessment,
        )

    def test_admin_can_archive_assessment_without_hiding_it_from_staff(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('delete_assessment', args=[self.assessment.pk]),
            {'action': 'archive'},
        )

        self.assertRedirects(response, reverse('assessment_list'))
        self.assertTrue(AdminArchivedRecord.objects.filter(
            record_type='assessment',
            record_id=self.assessment.pk,
        ).exists())
        self.assertFalse(RoleDeletedRecord.objects.filter(
            role='admin',
            record_type='assessment',
            record_id=self.assessment.pk,
        ).exists())
        admin_assessments = self.client.get(reverse('assessment_list'))
        admin_followups = self.client.get(reverse('followup_list'))
        self.assertNotIn(self.assessment, admin_assessments.context['assessments'])
        self.assertNotIn(self.followup, admin_followups.context['followups'])

        self.client.force_login(self.staff)
        staff_assessments = self.client.get(reverse('assessment_list'))
        staff_followups = self.client.get(reverse('followup_list'))
        self.assertIn(self.assessment, staff_assessments.context['assessments'])
        self.assertIn(self.followup, staff_followups.context['followups'])

        self.client.force_login(self.admin)
        self.client.post(reverse('archived_records'), {
            'record_type': 'assessment',
            'record_id': self.assessment.pk,
            'action': 'restore',
        })
        restored_assessments = self.client.get(reverse('assessment_list'))
        self.assertIn(self.assessment, restored_assessments.context['assessments'])

    def test_admin_assessment_archive_confirmation_uses_modal(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('delete_assessment', args=[self.assessment.pk]),
            {'action': 'archive'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            'nutrition/_assessment_delete_confirmation.html',
        )
        self.assertContains(response, 'value="archive"')
        self.assertContains(response, 'Archive')

    def test_admin_can_archive_followup_without_hiding_it_from_staff(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('delete_followup', args=[self.followup.pk]),
            {'action': 'archive'},
        )

        self.assertRedirects(response, reverse('followup_list'))
        self.assertTrue(AdminArchivedRecord.objects.filter(
            record_type='followup',
            record_id=self.followup.pk,
        ).exists())
        self.assertFalse(RoleDeletedRecord.objects.filter(
            role='admin',
            record_type='followup',
            record_id=self.followup.pk,
        ).exists())
        admin_followups = self.client.get(reverse('followup_list'))
        self.assertNotIn(self.followup, admin_followups.context['followups'])

        self.client.force_login(self.staff)
        staff_followups = self.client.get(reverse('followup_list'))
        self.assertIn(self.followup, staff_followups.context['followups'])

    def test_admin_delete_hides_assessment_and_followups_from_admin_only(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('delete_assessment', args=[self.assessment.pk]),
            {'action': 'delete'},
        )

        self.assertRedirects(response, reverse('assessment_list'))
        self.assertTrue(NutritionAssessment.all_objects.filter(pk=self.assessment.pk).exists())
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=self.followup.pk).exists())
        self.assertFalse(AdminArchivedRecord.objects.filter(
            record_type='assessment',
            record_id=self.assessment.pk,
        ).exists())
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='admin',
            record_type='assessment',
            record_id=self.assessment.pk,
        ).exists())
        self.assertNotIn(
            self.assessment,
            self.client.get(reverse('assessment_list')).context['assessments'],
        )
        self.assertNotIn(
            self.followup,
            self.client.get(reverse('followup_list')).context['followups'],
        )

        self.client.force_login(self.staff)
        self.assertIn(
            self.assessment,
            self.client.get(reverse('assessment_list')).context['assessments'],
        )
        self.assertIn(
            self.followup,
            self.client.get(reverse('followup_list')).context['followups'],
        )

    def test_admin_delete_hides_followup_from_admin_only(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('delete_followup', args=[self.followup.pk]),
            {'action': 'delete'},
        )

        self.assertRedirects(response, reverse('followup_list'))
        self.assertTrue(FollowUpRecord.all_objects.filter(pk=self.followup.pk).exists())
        self.assertFalse(AdminArchivedRecord.objects.filter(
            record_type='followup',
            record_id=self.followup.pk,
        ).exists())
        self.assertTrue(RoleDeletedRecord.objects.filter(
            role='admin',
            record_type='followup',
            record_id=self.followup.pk,
        ).exists())
        self.assertNotIn(
            self.followup,
            self.client.get(reverse('followup_list')).context['followups'],
        )

        self.client.force_login(self.staff)
        self.assertIn(
            self.followup,
            self.client.get(reverse('followup_list')).context['followups'],
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
