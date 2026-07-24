from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("api-guide/", views.api_guide, name="api_guide"),
    path("users/<str:username>/", views.public_profile, name="public_profile"),
]

for prefix, kind in (("posts", "post"), ("notes", "note"), ("projects", "project")):
    urlpatterns += [
        path(f"{prefix}/", getattr(views, f"{kind}_list"), name=f"{kind}_list"),
        path(f"{prefix}/add/", getattr(views, f"{kind}_add"), name=f"{kind}_add"),
        path(
            f"{prefix}/<slug:slug>/update/",
            getattr(views, f"{kind}_update"),
            name=f"{kind}_update",
        ),
        path(
            f"{prefix}/<slug:slug>/delete/",
            getattr(views, f"{kind}_delete"),
            name=f"{kind}_delete",
        ),
        path(
            f"{prefix}/<slug:slug>/download/",
            getattr(views, f"{kind}_download"),
            name=f"{kind}_download",
        ),
        path(
            f"{prefix}/<slug:slug>/",
            getattr(views, f"{kind}_detail"),
            name=f"{kind}_detail",
        ),
    ]
