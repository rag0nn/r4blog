from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .crypto import decrypt_text


class ActiveContentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class ContentBase(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="%(class)ss"
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=340, unique=True)
    encrypted_content = models.TextField()
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveContentManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ("-updated_at",)
        base_manager_name = "all_objects"
        default_manager_name = "objects"

    @property
    def markdown(self):
        return decrypt_text(self.encrypted_content)

    @property
    def is_public(self):
        return self.visibility == self.Visibility.PUBLIC

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def __str__(self):
        return self.title


class Post(ContentBase):
    pass


class Note(ContentBase):
    pass


class Project(ContentBase):
    pass


class ImmutableRevisionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Revision records are append-only and cannot be updated.")

    def delete(self):
        raise ValidationError("Revision records are append-only and cannot be deleted.")


class RevisionManager(models.Manager.from_queryset(ImmutableRevisionQuerySet)):
    def create(self, **kwargs):
        raise ValidationError("Revision records must be created by the content service.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Revision records must be created by the content service.")

    def append(self, **kwargs):
        revision = self.model(**kwargs)
        revision._service_create = True
        revision.save(force_insert=True)
        return revision


class RevisionBase(models.Model):
    revision_number = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    timestamp = models.DateTimeField(default=timezone.now, editable=False)
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=340)
    visibility = models.CharField(max_length=10, choices=ContentBase.Visibility.choices)
    encrypted_content = models.TextField()
    content_hash = models.CharField(max_length=64)
    previous_hash = models.CharField(max_length=64)
    chain_hash = models.CharField(max_length=64, unique=True)

    objects = RevisionManager()

    class Meta:
        abstract = True
        ordering = ("revision_number",)

    def save(self, *args, **kwargs):
        if self.pk or not getattr(self, "_service_create", False):
            raise ValidationError("Revision records are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Revision records are append-only and cannot be deleted.")

    def __str__(self):
        return f"{self.slug} revision {self.revision_number}"


class PostRevision(RevisionBase):
    post = models.ForeignKey(Post, on_delete=models.PROTECT, related_name="revisions")

    class Meta(RevisionBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("post", "revision_number"), name="unique_post_revision_number"
            )
        ]


class NoteRevision(RevisionBase):
    note = models.ForeignKey(Note, on_delete=models.PROTECT, related_name="revisions")

    class Meta(RevisionBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("note", "revision_number"), name="unique_note_revision_number"
            )
        ]


class ProjectRevision(RevisionBase):
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="revisions"
    )

    class Meta(RevisionBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("project", "revision_number"),
                name="unique_project_revision_number",
            )
        ]

