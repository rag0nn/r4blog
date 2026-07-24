from django.urls import path

from . import views


urlpatterns = [
    path("auth/token/", views.TokenLoginView.as_view(), name="api_token"),
    path("auth/revoke/", views.TokenRevokeView.as_view(), name="api_token_revoke"),
    path("posts/", views.PostCreateView.as_view(), name="api_post_create"),
    path(
        "posts/<slug:slug>/",
        views.PostUpdateView.as_view(),
        name="api_post_update",
    ),
    path(
        "posts/<slug:slug>/download/",
        views.PostDownloadView.as_view(),
        name="api_post_download",
    ),
    path("notes/", views.NoteCreateView.as_view(), name="api_note_create"),
    path(
        "notes/<slug:slug>/",
        views.NoteUpdateView.as_view(),
        name="api_note_update",
    ),
    path(
        "notes/<slug:slug>/download/",
        views.NoteDownloadView.as_view(),
        name="api_note_download",
    ),
    path("projects/", views.ProjectCreateView.as_view(), name="api_project_create"),
    path(
        "projects/<slug:slug>/",
        views.ProjectUpdateView.as_view(),
        name="api_project_update",
    ),
    path(
        "projects/<slug:slug>/download/",
        views.ProjectDownloadView.as_view(),
        name="api_project_download",
    ),
]
