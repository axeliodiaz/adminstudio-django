from django.conf import settings
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Instructor(SoftDeletableModel, UUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructor"
    )

    # Optional profile information
    profile_image = models.ImageField(
        upload_to="instructors/profile_images/", blank=True, null=True
    )
    description = models.TextField(blank=True, default="")
    tagline = models.CharField(max_length=140, blank=True, default="")

    # Social and contact
    website_url = models.URLField(blank=True, default="")
    instagram_username = models.CharField(max_length=100, blank=True, default="")
    tiktok_username = models.CharField(max_length=100, blank=True, default="")

    # Professional metadata
    is_verified = models.BooleanField(default=False)
    instructor_since = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=120, blank=True, default="")

    # Last playlist used per platform
    last_spotify_playlist = models.URLField(blank=True, default="")
    last_apple_music_playlist = models.URLField(blank=True, default="")
    last_youtube_music_playlist = models.URLField(blank=True, default="")

    def __str__(self):
        return self.user.username
