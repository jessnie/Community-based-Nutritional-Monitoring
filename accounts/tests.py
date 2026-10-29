from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
