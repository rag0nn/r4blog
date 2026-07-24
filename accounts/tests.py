from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AccountTests(TestCase):
    def test_registration_requires_unique_email_and_creates_profile(self):
        payload = {
            "username": "newuser",
            "email": "person@example.com",
            "password1": "VeryStrongPass123!",
            "password2": "VeryStrongPass123!",
        }
        response = self.client.post(reverse("register"), payload)
        user = get_user_model().objects.get(username="newuser")
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(user.profile.avatar, "default")
        self.assertEqual(user.profile.avatar_path, "blog/avatars/default.svg")

        self.client.logout()
        payload["username"] = "another"
        payload["email"] = "PERSON@example.com"
        response = self.client.post(reverse("register"), payload)
        self.assertContains(response, "already uses this email", status_code=200)

    def test_profile_and_password_reset_pages(self):
        user = get_user_model().objects.create_user("member", password="Pass12345!")
        self.assertEqual(self.client.get(reverse("profile")).status_code, 302)
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("profile")), "Choose an avatar")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)

    def test_login_and_register_expose_english_and_turkish_interface_text(self):
        login_response = self.client.get(reverse("login"))
        self.assertContains(login_response, "Username")
        self.assertContains(login_response, "Kullanıcı adı")
        self.assertContains(login_response, "Forgot your password?")
        self.assertContains(login_response, "Parolanı mı unuttun?")

        register_response = self.client.get(reverse("register"))
        self.assertContains(register_response, "Email address")
        self.assertContains(register_response, "E-posta adresi")
        self.assertContains(register_response, "Password confirmation")
        self.assertContains(register_response, "Parola doğrulama")
        self.assertContains(register_response, 'data-language-content="tr"')
