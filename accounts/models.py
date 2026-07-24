from django.conf import settings
from django.db import models

from .constants import AVATAR_CHOICES, AVATAR_PATHS


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    avatar = models.CharField(max_length=40, choices=AVATAR_CHOICES, default="default")

    @property
    def avatar_path(self):
        return AVATAR_PATHS.get(self.avatar, AVATAR_PATHS["default"])

    def __str__(self):
        return f"{self.user.username}'s profile"

