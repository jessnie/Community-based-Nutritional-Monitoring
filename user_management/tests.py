from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase


class UserManagementPageTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )

    def test_admin_can_open_user_management_list(self):
        get_user_model().objects.create_user(
            username="staff",
            email="staff@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("user_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user_management/user_list.html")
        self.assertContains(response, "staff")

    def test_non_admin_cannot_open_user_management_list(self):
        staff = get_user_model().objects.create_user(
            username="staff",
            password="test-password",
        )
        self.client.force_login(staff)

        response = self.client.get(reverse("user_list"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('login')}?next={reverse('user_list')}",
        )

    def test_admin_can_edit_user_without_changing_password(self):
        user = get_user_model().objects.create_user(
            username="staff",
            first_name="Old",
            password="original-password",
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("edit_user", args=[user.pk]),
            {
                "username": "staff",
                "first_name": "Updated",
                "last_name": "",
                "email": "",
                "password": "",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("user_list"))
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")
        self.assertTrue(user.check_password("original-password"))

    def test_admin_can_delete_staff_after_confirmation(self):
        user = get_user_model().objects.create_user(username="staff")
        self.client.force_login(self.admin)

        confirm_response = self.client.get(reverse("delete_user", args=[user.pk]))
        self.assertEqual(confirm_response.status_code, 200)
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

        response = self.client.post(reverse("delete_user", args=[user.pk]))

        self.assertRedirects(response, reverse("user_list"))
        self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())

    def test_admin_cannot_delete_self_but_can_remove_duplicate_admin(self):
        another_admin = get_user_model().objects.create_superuser(
            username="another-admin",
            email="another-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)

        self.client.post(reverse("delete_user", args=[self.admin.pk]))
        self.client.post(reverse("delete_user", args=[another_admin.pk]))

        self.assertTrue(
            get_user_model().objects.filter(pk=self.admin.pk).exists()
        )
        self.assertFalse(
            get_user_model().objects.filter(pk=another_admin.pk).exists()
        )
