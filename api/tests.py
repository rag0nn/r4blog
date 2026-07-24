from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from content.models import Note, Post, Project
from content.services import create_content


TEST_KEY = "SvV8NtBeKaZGCNilJGrS-Gd6fQ8KLGWDpJ4A0a6IaUo="


@override_settings(CONTENT_ENCRYPTION_KEY=TEST_KEY)
class ContentApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="Pass12345!")
        self.other = User.objects.create_user("other", password="Pass12345!")
        self.staff = User.objects.create_user("staff", password="Pass12345!", is_staff=True)

    def authenticate(self, user=None):
        user = user or self.owner
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return token

    def test_token_login_and_revoke(self):
        response = self.client.post(
            reverse("api_token"), {"username": "owner", "password": "Pass12345!"}
        )
        self.assertEqual(response.status_code, 200)
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.post(reverse("api_token_revoke")).status_code, 204)
        self.assertEqual(
            self.client.post(
                reverse("api_post_create"),
                {"markdown": "# Fails\nBody", "visibility": "public"},
            ).status_code,
            401,
        )

    def test_separate_create_endpoints_and_no_list_or_delete(self):
        self.authenticate()
        cases = (
            ("api_post_create", Post, "API Post"),
            ("api_note_create", Note, "API Note"),
            ("api_project_create", Project, "API Project"),
        )
        for route, model, title in cases:
            response = self.client.post(
                reverse(route),
                {"markdown": f"# {title}\nBody", "visibility": "private"},
                format="json",
            )
            self.assertEqual(response.status_code, 201)
            self.assertTrue(model.objects.filter(title=title, owner=self.owner).exists())
            self.assertEqual(self.client.get(reverse(route)).status_code, 405)

        post = Post.objects.get(title="API Post")
        update_url = reverse("api_post_update", args=[post.slug])
        self.assertEqual(self.client.delete(update_url).status_code, 405)
        self.assertEqual(self.client.get(update_url).status_code, 405)

    def test_file_create_and_owner_update(self):
        self.authenticate()
        upload = SimpleUploadedFile("note.md", b"# File Note\nUploaded body")
        response = self.client.post(
            reverse("api_note_create"),
            {"file": upload, "visibility": "public"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        note = Note.objects.get(slug="file-note")
        response = self.client.patch(
            reverse("api_note_update", args=[note.slug]),
            {"markdown": "# Renamed Note\nChanged", "visibility": "private"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.slug, "renamed-note")
        self.assertEqual(note.revisions.count(), 2)

    def test_cannot_choose_owner_or_update_another_users_content(self):
        foreign = create_content(Post, self.other, "# Foreign\nBody", "public")
        self.authenticate()
        response = self.client.post(
            reverse("api_post_create"),
            {
                "markdown": "# Mine\nBody",
                "visibility": "public",
                "owner": self.other.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.get(slug="mine").owner, self.owner)
        response = self.client.patch(
            reverse("api_post_update", args=[foreign.slug]),
            {"visibility": "private"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_public_and_private_download_permissions(self):
        public = create_content(Project, self.owner, "# Open Project\nPublic", "public")
        private = create_content(Project, self.owner, "# Secret Project\nPrivate", "private")
        public_url = reverse("api_project_download", args=[public.slug])
        private_url = reverse("api_project_download", args=[private.slug])
        response = self.client.get(public_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), public.markdown)
        self.assertEqual(self.client.get(private_url).status_code, 404)
        self.authenticate(self.owner)
        response = self.client.get(private_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.authenticate(self.staff)
        self.assertEqual(self.client.get(private_url).status_code, 200)

    def test_api_validation_for_h1_double_input_and_file_constraints(self):
        self.authenticate()
        response = self.client.post(
            reverse("api_post_create"), {"markdown": "No heading"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("api_post_create"),
            {
                "markdown": "# Manual",
                "file": SimpleUploadedFile("also.md", b"# File"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("api_post_create"),
            {"file": SimpleUploadedFile("wrong.txt", b"# Wrong")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
