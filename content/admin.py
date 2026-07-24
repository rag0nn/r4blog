from django.contrib import admin

from .models import Note, NoteRevision, Post, PostRevision, Project, ProjectRevision


class ContentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "owner",
        "visibility",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_filter = ("visibility", "is_deleted", "created_at", "updated_at")
    search_fields = ("title", "slug", "owner__username")
    readonly_fields = (
        "owner",
        "title",
        "slug",
        "encrypted_content",
        "visibility",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
    )

    def get_queryset(self, request):
        return self.model.all_objects.select_related("owner")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RevisionAdmin(admin.ModelAdmin):
    list_display = (
        "target",
        "revision_number",
        "actor",
        "timestamp",
        "content_hash",
        "chain_hash",
    )
    list_filter = ("visibility", "timestamp")
    search_fields = ("title", "slug", "actor__username", "content_hash", "chain_hash")

    def target(self, obj):
        return getattr(obj, self.content_field)

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Post)
class PostAdmin(ContentAdmin):
    pass


@admin.register(Note)
class NoteAdmin(ContentAdmin):
    pass


@admin.register(Project)
class ProjectAdmin(ContentAdmin):
    pass


@admin.register(PostRevision)
class PostRevisionAdmin(RevisionAdmin):
    content_field = "post"


@admin.register(NoteRevision)
class NoteRevisionAdmin(RevisionAdmin):
    content_field = "note"


@admin.register(ProjectRevision)
class ProjectRevisionAdmin(RevisionAdmin):
    content_field = "project"
