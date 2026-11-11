from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import SystemSettings


class AccountSettingsTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='settingsstaff',
            email='staff@example.com',
            password='original-test-password',
        )
        self.admin = get_user_model().objects.create_superuser(
            username='settingsadmin',
            email='admin@example.com',
            password='original-test-password',
        )

    def test_staff_cannot_open_settings_or_update_profile(self):
        self.client.force_login(self.staff)

        page = self.client.get(reverse('account_settings'))
        self.assertRedirects(page, reverse('dashboard'))

        response = self.client.post(reverse('account_settings'), {
            'form_type': 'profile',
            'first_name': 'Updated',
            'last_name': 'Staff',
            'email': 'updated@example.com',
        })

        self.assertRedirects(response, reverse('dashboard'))
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, '')
        self.assertEqual(self.staff.email, 'staff@example.com')

    def test_admin_password_change_keeps_admin_authenticated(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('account_settings'), {
            'form_type': 'password',
            'old_password': 'original-test-password',
            'new_password1': 'new-secure-test-password-2026',
            'new_password2': 'new-secure-test-password-2026',
        })

        self.assertRedirects(response, reverse('account_settings'))
        self.assertTrue(
            self.client.login(
                username='settingsadmin',
                password='new-secure-test-password-2026',
            )
        )

    def test_admin_can_update_system_information(self):
        self.client.force_login(self.admin)
        page = self.client.get(reverse('account_settings'))

        self.assertEqual(page.status_code, 200)
        self.assertIsNotNone(page.context['system_form'])
        self.assertContains(page, 'System Information')

        response = self.client.post(reverse('account_settings'), {
            'form_type': 'system',
            'barangay_name': 'Barangay Example',
            'health_center_name': 'Community Health Center',
            'contact_number': '09170000000',
            'contact_email': 'health@example.com',
            'address': 'Example Address',
        })

        self.assertRedirects(response, reverse('account_settings'))
        settings = page.context['system_form'].instance
        settings.refresh_from_db()
        self.assertEqual(settings.barangay_name, 'Barangay Example')
        self.assertEqual(settings.contact_email, 'health@example.com')

    def test_staff_cannot_update_system_information(self):
        self.client.force_login(self.staff)
        settings = SystemSettings.objects.create()

        response = self.client.post(reverse('account_settings'), {
            'form_type': 'system',
            'barangay_name': 'Unauthorized Change',
            'health_center_name': 'Changed',
            'contact_number': '',
            'contact_email': '',
            'address': '',
        })

        self.assertRedirects(response, reverse('dashboard'))
        settings.refresh_from_db()
        self.assertEqual(settings.barangay_name, 'Barangay Can-Uguib')


class AuthenticatedResponseCacheTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='cachetest',
            password='test-password',
        )
        self.client.force_login(self.user)

    def assert_not_cached(self, response):
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['Pragma'], 'no-cache')
        self.assertEqual(response['Expires'], '0')

    def test_authenticated_dashboard_response_is_not_cached(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assert_not_cached(response)
        self.assertContains(
            response,
            'window.addEventListener("popstate", goToLogin)',
        )
        self.assertContains(
            response,
            'window.history.pushState({ logoutOnBack: true }, "", window.location.href);',
        )
        self.assertContains(
            response,
            f'window.location.replace("{reverse("logout")}");',
        )
        self.assertContains(response, 'class="bi bi-house-door-fill"')
        self.assertContains(response, f'href="{reverse("logout")}"')
        self.assertNotContains(response, f'href="{reverse("account_settings")}"')

    def test_superuser_dashboard_request_redirects_to_admin_dashboard(self):
        admin = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('admin_dashboard'))
        admin_response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(
            admin_response,
            'window.addEventListener("popstate", goToLogin)',
        )
        self.assertContains(
            admin_response,
            'window.history.pushState({ logoutOnBack: true }, "", window.location.href);',
        )
        self.assertContains(admin_response, 'class="bi bi-house-door-fill"')

    def test_logout_redirect_is_not_cached(self):
        response = self.client.get(reverse('logout'))

        self.assertRedirects(response, reverse('login'))
        self.assert_not_cached(response)
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            dashboard_response,
            f'{reverse("login")}?next={reverse("dashboard")}',
        )
