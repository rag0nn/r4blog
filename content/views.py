from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ContentEditorForm
from .markdown import markdown_preview, render_markdown
from .models import Note, Post, Project
from .services import (
    can_view,
    create_content,
    delete_content,
    search_visible,
    update_content,
)


CONTENT_CONFIG = {
    "post": {
        "model": Post,
        "singular": "Post",
        "plural": "Posts",
        "singular_tr": "Yazı",
        "plural_tr": "Yazılar",
        "prefix": "posts",
    },
    "note": {
        "model": Note,
        "singular": "Note",
        "plural": "Notes",
        "singular_tr": "Not",
        "plural_tr": "Notlar",
        "prefix": "notes",
    },
    "project": {
        "model": Project,
        "singular": "Project",
        "plural": "Projects",
        "singular_tr": "Proje",
        "plural_tr": "Projeler",
        "prefix": "projects",
    },
}


def _config(kind):
    config = CONTENT_CONFIG[kind].copy()
    config["kind"] = kind
    config["list_url"] = f"{kind}_list"
    config["detail_url"] = f"{kind}_detail"
    config["add_url"] = f"{kind}_add"
    config["update_url"] = f"{kind}_update"
    config["delete_url"] = f"{kind}_delete"
    config["download_url"] = f"{kind}_download"
    return config


def _get_visible_or_404(kind, slug, user):
    instance = get_object_or_404(_config(kind)["model"].objects, slug=slug)
    if not can_view(instance, user):
        raise Http404
    return instance


def home(request):
    cards = []
    for kind in ("post", "note", "project"):
        config = _config(kind)
        item = (
            config["model"]
            .objects.filter(visibility="public")
            .select_related("owner__profile")
            .order_by("-updated_at")
            .first()
        )
        cards.append(
            {
                "config": config,
                "item": item,
                "preview": markdown_preview(item.markdown) if item else "",
            }
        )
    return render(
        request,
        "content/home.html",
        {"cards": cards, "user_count": get_user_model().objects.count()},
    )


def content_list(request, kind):
    config = _config(kind)
    query = request.GET.get("q", "").strip()
    if query:
        items = search_visible(config["model"], request.user, query)
    else:
        items = list(
            config["model"]
            .objects.filter(visibility="public")
            .select_related("owner__profile")
            .order_by("-updated_at")
        )
    page_obj = Paginator(items, 10).get_page(request.GET.get("page"))
    own_items = []
    if request.user.is_authenticated:
        own_items = config["model"].objects.filter(owner=request.user)[:10]
    response = render(
        request,
        "content/content_list.html",
        {
            "config": config,
            "page_obj": page_obj,
            "own_items": own_items,
            "query": query,
        },
    )
    if request.user.is_authenticated:
        response["Cache-Control"] = "private, no-store"
    return response


@never_cache
def content_detail(request, kind, slug):
    config = _config(kind)
    item = _get_visible_or_404(kind, slug, request.user)
    response = render(
        request,
        "content/content_detail.html",
        {"config": config, "item": item, "rendered_content": render_markdown(item.markdown)},
    )
    if item.visibility == "private":
        response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_http_methods(["GET", "POST"])
def content_add(request, kind):
    config = _config(kind)
    form = ContentEditorForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = create_content(
            config["model"],
            request.user,
            form.cleaned_data["markdown"],
            form.cleaned_data["visibility"],
        )
        messages.success(request, f"{config['singular']} created successfully.")
        return redirect(config["detail_url"], slug=item.slug)
    return render(
        request,
        "content/content_form.html",
        {"config": config, "form": form, "action": "Add"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def content_update(request, kind, slug):
    config = _config(kind)
    item = get_object_or_404(config["model"].objects, slug=slug, owner=request.user)
    if request.method == "POST":
        form = ContentEditorForm(request.POST, request.FILES)
        if form.is_valid():
            item = update_content(
                item,
                request.user,
                form.cleaned_data["markdown"],
                form.cleaned_data["visibility"],
            )
            messages.success(request, f"{config['singular']} updated successfully.")
            return redirect(config["detail_url"], slug=item.slug)
    else:
        form = ContentEditorForm(
            initial={"manual_content": item.markdown, "visibility": item.visibility}
        )
    return render(
        request,
        "content/content_form.html",
        {"config": config, "form": form, "action": "Update", "item": item},
    )


@login_required
@require_http_methods(["GET", "POST"])
def content_delete(request, kind, slug):
    config = _config(kind)
    item = get_object_or_404(config["model"].objects, slug=slug, owner=request.user)
    if request.method == "POST":
        delete_content(item, request.user)
        messages.success(request, f"{config['singular']} deleted successfully.")
        return redirect(config["list_url"])
    return render(
        request, "content/content_confirm_delete.html", {"config": config, "item": item}
    )


@never_cache
def content_download(request, kind, slug):
    item = _get_visible_or_404(kind, slug, request.user)
    response = HttpResponse(item.markdown, content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{item.slug}.md"'
    response["X-Content-Type-Options"] = "nosniff"
    if item.visibility == "private":
        response["Cache-Control"] = "private, no-store"
    return response


def public_profile(request, username):
    profile_user = get_object_or_404(get_user_model(), username=username)
    groups = []
    contains_private = False
    own_profile = request.user.is_authenticated and request.user.pk == profile_user.pk
    for kind in ("post", "note", "project"):
        config = _config(kind)
        public_items = config["model"].objects.filter(
            owner=profile_user, visibility="public"
        )
        private_items = (
            config["model"].objects.filter(owner=profile_user, visibility="private")
            if own_profile or (request.user.is_authenticated and request.user.is_staff)
            else config["model"].objects.none()
        )
        contains_private = contains_private or private_items.exists()
        groups.append(
            {"config": config, "public_items": public_items, "private_items": private_items}
        )
    response = render(
        request,
        "content/public_profile.html",
        {"profile_user": profile_user, "groups": groups, "own_profile": own_profile},
    )
    if own_profile or contains_private:
        response["Cache-Control"] = "private, no-store"
    return response


def about(request):
    return render(request, "content/about.html")


def api_guide(request):
    return render(request, "content/api_guide.html")


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def _kind_view(handler, kind):
    @wraps(handler)
    def wrapped(request, *args, **kwargs):
        return handler(request, kind, *args, **kwargs)

    return wrapped


post_list = _kind_view(content_list, "post")
note_list = _kind_view(content_list, "note")
project_list = _kind_view(content_list, "project")
post_detail = _kind_view(content_detail, "post")
note_detail = _kind_view(content_detail, "note")
project_detail = _kind_view(content_detail, "project")
post_add = _kind_view(content_add, "post")
note_add = _kind_view(content_add, "note")
project_add = _kind_view(content_add, "project")
post_update = _kind_view(content_update, "post")
note_update = _kind_view(content_update, "note")
project_update = _kind_view(content_update, "project")
post_delete = _kind_view(content_delete, "post")
note_delete = _kind_view(content_delete, "note")
project_delete = _kind_view(content_delete, "project")
post_download = _kind_view(content_download, "post")
note_download = _kind_view(content_download, "note")
project_download = _kind_view(content_download, "project")
