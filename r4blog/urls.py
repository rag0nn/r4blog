from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views
from content import views as content_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("profile/", account_views.profile, name="profile"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),
    path("api/v1/", include("api.urls")),
    path("", include("content.urls")),
]

handler404 = content_views.custom_404
