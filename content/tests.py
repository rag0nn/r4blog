from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .crypto import decrypt_text, encrypt_text
from .forms import ContentEditorForm
from .markdown import extract_title, render_markdown
from .models import Note, NoteRevision, Post, PostRevision, Project, ProjectRevision
from .services import (
    create_content,
    delete_content,
    search_visible,
    update_content,
    verify_revision_chain,
)


TEST_KEY = "SvV8NtBeKaZGCNilJGrS-Gd6fQ8KLGWDpJ4A0a6IaUo="


@override_settings(CONTENT_ENCRYPTION_KEY=TEST_KEY)
class ContentModelAndServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="owner", email="owner@example.com", password="StrongPass123!"
        )

    def test_content_types_use_separate_tables_and_revision_tables(self):
        tables = set(connection.introspection.table_names())
        expected = {
            Post._meta.db_table,
            Note._meta.db_table,
            Project._meta.db_table,
            PostRevision._meta.db_table,
            NoteRevision._meta.db_table,
            ProjectRevision._meta.db_table,
        }
        self.assertTrue(expected.issubset(tables))
        self.assertEqual(len(expected), 6)

    def test_each_type_creates_encrypted_content_and_own_revision(self):
        pairs = (
            (Post, PostRevision, "post"),
            (Note, NoteRevision, "note"),
            (Project, ProjectRevision, "project"),
        )
        plaintext = "# Beşiktaş Sponsoru\n\nSecret searchable body"
        for model, revision_model, relation in pairs:
            item = create_content(model, self.user, plaintext, "private")
            self.assertEqual(item.title, "Beşiktaş Sponsoru")
            self.assertEqual(item.slug, "besiktas-sponsoru")
            self.assertNotIn("Secret searchable body", item.encrypted_content)
            self.assertEqual(item.markdown, plaintext)
            revision = revision_model.objects.get(**{relation: item})
            self.assertEqual(revision.revision_number, 1)
            self.assertEqual(revision.previous_hash, "0" * 64)
            self.assertNotIn("Secret", revision.encrypted_content)

    def test_slug_collisions_and_title_changes_are_deterministic(self):
        first = create_content(Post, self.user, "# Same Title\nOne", "public")
        second = create_content(Post, self.user, "# Same Title\nTwo", "public")
        note = create_content(Note, self.user, "# Same Title\nNote", "public")
        self.assertEqual(first.slug, "same-title")
        self.assertEqual(second.slug, "same-title-2")
        self.assertEqual(note.slug, "same-title")
        changed = update_content(first, self.user, "# Same Title\nChanged", "private")
        self.assertEqual(changed.slug, "same-title")
        changed = update_content(first, self.user, "# Another Title\nChanged", "private")
        self.assertEqual(changed.slug, "another-title")

    def test_timestamps_and_revision_hash_chain(self):
        item = create_content(Post, self.user, "# Version One\nBody", "public")
        created_at = item.created_at
        item = update_content(item, self.user, "# Version Two\nChanged", "private")
        revisions = list(item.revisions.all())
        self.assertEqual(item.created_at, created_at)
        self.assertGreaterEqual(item.updated_at, created_at)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[1].previous_hash, revisions[0].chain_hash)
        self.assertNotEqual(revisions[0].chain_hash, revisions[1].chain_hash)
        self.assertEqual(revisions[1].actor, self.user)
        self.assertTrue(verify_revision_chain(item))

    def test_revision_verifier_detects_database_level_tampering(self):
        item = create_content(Post, self.user, "# Verified\nBody", "public")
        revision = item.revisions.get()
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {PostRevision._meta.db_table} SET chain_hash = %s WHERE id = %s",
                ["f" * 64, revision.pk],
            )
        self.assertFalse(verify_revision_chain(item))

    def test_revision_records_reject_update_delete_and_direct_create(self):
        item = create_content(Post, self.user, "# Immutable\nBody", "public")
        revision = item.revisions.get()
        revision.title = "Tampered"
        with self.assertRaises(ValidationError):
            revision.save()
        with self.assertRaises(ValidationError):
            revision.delete()
        with self.assertRaises(ValidationError):
            PostRevision.objects.filter(pk=revision.pk).update(title="Tampered")
        with self.assertRaises(ValidationError):
            PostRevision.objects.create(
                post=item,
                revision_number=2,
                actor=self.user,
                title=item.title,
                slug=item.slug,
                visibility=item.visibility,
                encrypted_content=item.encrypted_content,
                content_hash="a" * 64,
                previous_hash="b" * 64,
                chain_hash="c" * 64,
            )

    def test_create_and_revision_are_atomic(self):
        with patch("content.services.append_revision", side_effect=RuntimeError("fail")):
            with self.assertRaises(RuntimeError):
                create_content(Post, self.user, "# Rolled Back\nBody", "public")
        self.assertFalse(Post.objects.filter(slug="rolled-back").exists())

    def test_soft_delete_hides_content_but_keeps_revision(self):
        item = create_content(Post, self.user, "# Gone\nBody", "public")
        revision_pk = item.revisions.get().pk
        delete_content(item, self.user)
        self.assertFalse(Post.objects.filter(pk=item.pk).exists())
        self.assertTrue(Post.all_objects.get(pk=item.pk).is_deleted)
        self.assertTrue(PostRevision.objects.filter(pk=revision_pk).exists())

    def test_search_decrypts_only_authorized_candidates(self):
        other = get_user_model().objects.create_user("other", password="StrongPass123!")
        public = create_content(Post, other, "# Public\nNeedle public", "public")
        own_private = create_content(Post, self.user, "# Private\nNeedle own", "private")
        foreign_private = create_content(Post, other, "# Hidden\nNeedle hidden", "private")
        results = search_visible(Post, self.user, "needle")
        self.assertIn(public, results)
        self.assertIn(own_private, results)
        self.assertNotIn(foreign_private, results)
        anonymous_results = search_visible(Post, type("Anon", (), {"is_authenticated": False})(), "needle")
        self.assertEqual(anonymous_results, [public])

    def test_invalid_or_missing_encryption_key_is_clear(self):
        with override_settings(CONTENT_ENCRYPTION_KEY=""):
            with self.assertRaises(ImproperlyConfigured):
                encrypt_text("text")
        with override_settings(CONTENT_ENCRYPTION_KEY="not-a-fernet-key"):
            with self.assertRaises(ImproperlyConfigured):
                encrypt_text("text")
        with self.assertRaises(ImproperlyConfigured):
            decrypt_text(encrypt_text("text")[:-2] + "xx")

    def test_raw_html_and_supported_markdown_are_rendered(self):
        html = str(
            render_markdown(
                "# Rich\n\n<table><tr><td>raw</td></tr></table>\n\n```python\nprint('x')\n```"
            )
        )
        self.assertIn("<table>", html)
        self.assertIn("codehilite", html)
        self.assertNotIn("<h1", html)


@override_settings(CONTENT_ENCRYPTION_KEY=TEST_KEY)
class ContentValidationTests(TestCase):
    def test_first_nonempty_line_must_be_one_h1(self):
        self.assertEqual(extract_title("\n# Valid Title\nBody"), "Valid Title")
        for invalid in ("", "Text first\n# Later", "## H2", "#   "):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    extract_title(invalid)

    def test_form_rejects_double_input_wrong_extension_encoding_and_large_file(self):
        cases = [
            ContentEditorForm(
                {"manual_content": "# Manual", "visibility": "public"},
                {"markdown_file": SimpleUploadedFile("also.md", b"# File")},
            ),
            ContentEditorForm(
                {"visibility": "public"},
                {"markdown_file": SimpleUploadedFile("bad.txt", b"# File")},
            ),
            ContentEditorForm(
                {"visibility": "public"},
                {"markdown_file": SimpleUploadedFile("bad.md", b"\xff\xfe")},
            ),
            ContentEditorForm(
                {"manual_content": "# Big\n" + "x" * (2 * 1024 * 1024), "visibility": "public"}
            ),
        ]
        for form in cases:
            with self.subTest(form=form):
                self.assertFalse(form.is_valid())


@override_settings(CONTENT_ENCRYPTION_KEY=TEST_KEY)
class WebPermissionAndPageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", "owner@example.com", "Pass12345!")
        self.other = User.objects.create_user("other", "other@example.com", "Pass12345!")
        self.staff = User.objects.create_user(
            "staff", "staff@example.com", "Pass12345!", is_staff=True
        )
        self.public = create_content(Post, self.owner, "# Public Entry\nVisible body", "public")
        self.private = create_content(Post, self.owner, "# Private Entry\nSecret needle", "private")

    def test_private_detail_and_download_permissions(self):
        detail = reverse("post_detail", args=[self.private.slug])
        download = reverse("post_download", args=[self.private.slug])
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.get(download).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(detail)
        self.assertEqual(response.status_code, 200)
        self.assertIn("private", response["Cache-Control"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(response, "Secret needle")
        markup = response.content.decode()
        self.assertEqual(markup.count("#private-entry"), 1)
        self.assertLess(markup.index("Private Entry</h1>"), markup.index("detail-visibility"))
        self.assertEqual(markup.count('class="icon-action"'), 2)
        self.assertIn("fa-circle-arrow-down", markup)
        self.assertIn("fa-cloud-arrow-up", markup)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_update_delete_are_owner_only(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("post_update", args=[self.public.slug])).status_code, 404
        )
        self.assertEqual(
            self.client.post(reverse("post_delete", args=[self.public.slug])).status_code, 404
        )
        self.client.force_login(self.owner)
        response = self.client.post(reverse("post_delete", args=[self.public.slug]))
        self.assertRedirects(response, reverse("post_list"))
        self.assertEqual(self.client.get(reverse("post_detail", args=[self.public.slug])).status_code, 404)

    def test_web_create_routes_for_each_type_and_file_update(self):
        self.assertEqual(self.client.get(reverse("post_add")).status_code, 302)
        self.client.force_login(self.owner)
        cases = (
            ("post_add", Post, "Web Post"),
            ("note_add", Note, "Web Note"),
            ("project_add", Project, "Web Project"),
        )
        for route, model, title in cases:
            response = self.client.post(
                reverse(route),
                {"manual_content": f"# {title}\nBody", "visibility": "public"},
            )
            item = model.objects.get(title=title)
            self.assertRedirects(
                response, reverse(f"{model.__name__.lower()}_detail", args=[item.slug])
            )

        web_post = Post.objects.get(title="Web Post")
        response = self.client.post(
            reverse("post_update", args=[web_post.slug]),
            {
                "visibility": "private",
                "markdown_file": SimpleUploadedFile(
                    "updated.md", b"# Uploaded Update\nNew body"
                ),
            },
        )
        web_post.refresh_from_db()
        self.assertRedirects(
            response, reverse("post_detail", args=["uploaded-update"])
        )
        self.assertEqual(web_post.slug, "uploaded-update")
        self.assertEqual(web_post.visibility, "private")
        self.assertEqual(web_post.revisions.count(), 2)

    def test_list_search_does_not_leak_foreign_private_content(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("post_list"), {"q": "needle"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Private Entry")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("post_list"), {"q": "needle"})
        self.assertContains(response, "Private Entry")

    def test_home_latest_public_user_count_and_theme_controls(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Public Entry")
        self.assertNotContains(response, "Private Entry")
        self.assertContains(response, "registered users")
        self.assertContains(response, 'data-theme-choice="reading"')
        self.assertContains(response, 'class="bg-slider"')
        self.assertContains(response, 'class="theme-panel theme-reading"')
        self.assertContains(response, 'data-language-choice="tr"')
        self.assertContains(response, "theme.js")
        self.assertContains(response, "language.js")
        self.assertNotContains(response, 'class="brand"')
        self.assertNotContains(response, "R4Blog")
        self.assertContains(response, "r4blog · fikirler, notlar ve projeler.")
        markup = response.content.decode()
        self.assertLess(markup.index('class="account-nav"'), markup.index('class="theme-switcher"'))
        self.assertLess(markup.index('class="theme-switcher"'), markup.index('class="language-switcher"'))

        css = (settings.BASE_DIR / "static/css/site.css").read_text(encoding="utf-8")
        self.assertIn("width: 300vw", css)
        self.assertIn("#f6f3eb", css)
        self.assertIn("#efe9dc", css)
        self.assertIn("#457b9d", css)
        self.assertIn("#00bfa5", css)
        self.assertIn(".own-list .visibility { width: fit-content; justify-self: start; color: #2a9d65; background: var(--snow); }", css)
        self.assertIn('html[data-theme="reading"] .own-list .visibility', css)
        self.assertIn('html[data-theme="reading"] .detail-header { margin-right: -14px;', css)

    def test_about_us_title_and_public_list_color_hierarchy(self):
        response = self.client.get(reverse("about"))
        self.assertContains(response, "About Us")
        css = (settings.BASE_DIR / "static/css/site.css").read_text(encoding="utf-8")
        self.assertIn(".public-list", css)
        self.assertIn(".public-list { border-radius: 25px; padding: 26px; background: var(--red)", css)
        self.assertIn("background: var(--snow)", css)
        self.assertIn(".list-card:hover { border-color: var(--charcoal)", css)
        self.assertIn("background: var(--red); transform: translateY(-4px)", css)

    def test_api_guide_has_complete_language_sections(self):
        response = self.client.get(reverse("api_guide"))
        self.assertContains(response, 'data-language-content="en"')
        self.assertContains(response, 'data-language-content="tr"')
        self.assertContains(response, "Get and revoke a token")
        self.assertContains(response, "Token alma ve iptal etme")
        self.assertContains(response, "Validation and responses")
        self.assertContains(response, "Doğrulama ve cevaplar")
        self.assertContains(response, "[root]/api/v1/auth/token/", count=2)
        self.assertNotContains(response, "localhost:8000")
        language_script = (
            settings.BASE_DIR / "static/js/language.js"
        ).read_text(encoding="utf-8")
        self.assertIn("[data-language-content]", language_script)

    def test_public_profile_only_exposes_private_to_self_or_staff(self):
        url = reverse("public_profile", args=[self.owner.username])
        response = self.client.get(url)
        self.assertContains(response, "Public Entry")
        self.assertNotContains(response, "Private Entry")
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(url), "Private Entry")
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(url), "Private Entry")

    def test_list_paginates_at_ten(self):
        for index in range(10):
            create_content(Post, self.owner, f"# Entry {index}\nBody", "public")
        response = self.client.get(reverse("post_list"))
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)
