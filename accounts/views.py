from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from .forms import ProfileForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account has been created.")
        return redirect("profile")
    return render(request, "accounts/register.html", {"form": form})


@login_required
@never_cache
def profile(request):
    profile_obj = request.user.profile
    form = ProfileForm(request.POST or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your avatar has been updated.")
        return redirect("profile")
    response = render(request, "accounts/profile.html", {"form": form})
    response["Cache-Control"] = "private, no-store"
    return response
