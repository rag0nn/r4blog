import hashlib
import json
from datetime import timezone as datetime_timezone

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from slugify import slugify

from .crypto import decrypt_text, encrypt_text
from .markdown import extract_title, normalize_markdown
from .models import (
    Note,
    NoteRevision,
    Post,
    PostRevision,
    Project,
    ProjectRevision,
)


MODEL_META = {
    Post: (PostRevision, "post"),
    Note: (NoteRevision, "note"),
    Project: (ProjectRevision, "project"),
}


def unique_slug(model, title, current_pk=None):
    base = slugify(title, lowercase=True, separator="-") or "entry"
    base = base[:300].strip("-") or "entry"
    candidate = base
    suffix = 2
    queryset = model.all_objects.all()
    if current_pk:
        queryset = queryset.exclude(pk=current_pk)
    while queryset.filter(slug=candidate).exists():
        ending = f"-{suffix}"
        candidate = f"{base[: 340 - len(ending)]}{ending}"
        suffix += 1
    return candidate


def _canonical_timestamp(value):
    return (
        value.astimezone(datetime_timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _calculate_chain_hash(
    instance,
    actor_id,
    revision_number,
    timestamp,
    content_hash,
    previous_hash,
    title,
    slug,
    visibility,
):
    canonical = json.dumps(
        {
            "actor_id": actor_id,
            "content_hash": content_hash,
            "content_id": instance.pk,
            "content_type": type(instance).__name__,
            "previous_hash": previous_hash,
            "revision_number": revision_number,
            "slug": slug,
            "timestamp": _canonical_timestamp(timestamp),
            "title": title,
            "visibility": visibility,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_revision(instance, actor, plaintext):
    revision_model, content_field = MODEL_META[type(instance)]
    latest = (
        revision_model.objects.select_for_update()
        .filter(**{content_field: instance})
        .order_by("-revision_number")
        .first()
    )
    revision_number = latest.revision_number + 1 if latest else 1
    previous_hash = latest.chain_hash if latest else "0" * 64
    timestamp = timezone.now()
    content_hash = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    chain_hash = _calculate_chain_hash(
        instance,
        actor.pk,
        revision_number,
        timestamp,
        content_hash,
        previous_hash,
        instance.title,
        instance.slug,
        instance.visibility,
    )
    values = {
        content_field: instance,
        "revision_number": revision_number,
        "actor": actor,
        "timestamp": timestamp,
        "title": instance.title,
        "slug": instance.slug,
        "visibility": instance.visibility,
        "encrypted_content": encrypt_text(plaintext),
        "content_hash": content_hash,
        "previous_hash": previous_hash,
        "chain_hash": chain_hash,
    }
    return revision_model.objects.append(**values)


def verify_revision_chain(instance):
    revision_model, content_field = MODEL_META[type(instance)]
    previous_hash = "0" * 64
    expected_number = 1
    revisions = revision_model.objects.filter(**{content_field: instance}).order_by(
        "revision_number"
    )
    for revision in revisions:
        plaintext = decrypt_text(revision.encrypted_content)
        content_hash = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
        expected_chain_hash = _calculate_chain_hash(
            instance,
            revision.actor_id,
            revision.revision_number,
            revision.timestamp,
            revision.content_hash,
            revision.previous_hash,
            revision.title,
            revision.slug,
            revision.visibility,
        )
        if (
            revision.revision_number != expected_number
            or revision.previous_hash != previous_hash
            or revision.content_hash != content_hash
            or revision.chain_hash != expected_chain_hash
        ):
            return False
        previous_hash = revision.chain_hash
        expected_number += 1
    return expected_number > 1


@transaction.atomic
def create_content(model, owner, markdown, visibility):
    markdown = normalize_markdown(markdown)
    title = extract_title(markdown)
    if visibility not in dict(model.Visibility.choices):
        raise ValidationError("Visibility must be public or private.")
    instance = model.all_objects.create(
        owner=owner,
        title=title,
        slug=unique_slug(model, title),
        encrypted_content=encrypt_text(markdown),
        visibility=visibility,
    )
    append_revision(instance, owner, markdown)
    return instance


@transaction.atomic
def update_content(instance, actor, markdown=None, visibility=None):
    instance = type(instance).all_objects.select_for_update().get(pk=instance.pk)
    if instance.owner_id != actor.pk:
        raise PermissionDenied("Only the owner can update this content.")
    if instance.is_deleted:
        raise ValidationError("Deleted content cannot be updated.")
    markdown = instance.markdown if markdown is None else normalize_markdown(markdown)
    title = extract_title(markdown)
    visibility = visibility or instance.visibility
    if visibility not in dict(instance.Visibility.choices):
        raise ValidationError("Visibility must be public or private.")
    instance.title = title
    instance.slug = unique_slug(type(instance), title, current_pk=instance.pk)
    instance.encrypted_content = encrypt_text(markdown)
    instance.visibility = visibility
    instance.save()
    append_revision(instance, actor, markdown)
    return instance


@transaction.atomic
def delete_content(instance, actor):
    instance = type(instance).all_objects.select_for_update().get(pk=instance.pk)
    if instance.owner_id != actor.pk:
        raise PermissionDenied("Only the owner can delete this content.")
    if not instance.is_deleted:
        instance.soft_delete()
    return instance


def visible_to(queryset, user):
    public = Q(visibility="public")
    if user.is_authenticated:
        if user.is_staff:
            return queryset
        return queryset.filter(public | Q(owner=user))
    return queryset.filter(public)


def can_view(instance, user):
    return instance.visibility == "public" or (
        user.is_authenticated and (user.is_staff or instance.owner_id == user.pk)
    )


def search_visible(model, user, query):
    candidates = list(visible_to(model.objects.select_related("owner__profile"), user))
    query = query.strip().casefold()
    if not query:
        return candidates
    matches = []
    for item in candidates:
        if (
            query in item.title.casefold()
            or query in item.slug.casefold()
            or query in item.markdown.casefold()
        ):
            matches.append(item)
    return matches
