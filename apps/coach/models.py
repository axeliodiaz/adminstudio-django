from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.instructors.models import Instructor
from apps.schedules.models import Schedule


class ClassRating(SoftDeletableModel, UUIDModel, TimeStampedModel):
    schedule = models.OneToOneField(
        Schedule,
        on_delete=models.CASCADE,
        related_name="class_rating",
    )
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    rating_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.schedule_id} ({self.rating})"


class PlaylistTemplate(SoftDeletableModel, UUIDModel, TimeStampedModel):
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name="playlist_templates",
    )
    name = models.CharField(max_length=140)
    class_format = models.CharField(max_length=80, blank=True, default="")

    def __str__(self):
        return self.name


class ClassPlaylist(SoftDeletableModel, UUIDModel, TimeStampedModel):
    schedule = models.OneToOneField(
        Schedule,
        on_delete=models.CASCADE,
        related_name="playlist",
    )
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name="class_playlists",
    )
    title = models.CharField(max_length=255, blank=True, default="")
    total_duration_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title or str(self.schedule_id)


class PlaylistSegment(SoftDeletableModel, UUIDModel, TimeStampedModel):
    playlist = models.ForeignKey(
        ClassPlaylist,
        on_delete=models.CASCADE,
        related_name="segments",
    )
    name = models.CharField(max_length=140)
    order = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0)
    bpm_range = models.CharField(max_length=40, blank=True, default="")

    class Meta:
        ordering = ["order", "created"]

    def __str__(self):
        return self.name


class PlaylistTrack(SoftDeletableModel, UUIDModel, TimeStampedModel):
    segment = models.ForeignKey(
        PlaylistSegment,
        on_delete=models.CASCADE,
        related_name="tracks",
    )
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, blank=True, default="")
    bpm = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created"]

    def __str__(self):
        return self.title
