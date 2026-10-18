from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Address(SoftDeletableModel, UUIDModel, TimeStampedModel):
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Latitude for this address.",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Longitude for this address.",
    )

    def __str__(self):
        return self.address


class Studio(SoftDeletableModel, UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    address = models.ForeignKey(
        "Address",
        on_delete=models.SET_NULL,
        related_name="studios",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=False)
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def rooms_list(self):
        """Return related rooms as a concrete list to ease Pydantic serialization."""
        return list(self.rooms.all())


class Location(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """A sede (physical site) of a studio brand (CYC-455).

    Studio is the brand/identity (name, branding); Location is a place with
    an address and opening hours. Rooms belong to locations; the brand is
    reachable as ``location.studio``. Studio still carries the legacy
    address/hours fields until CYC-456 moves every reader to Location.
    """

    studio = models.ForeignKey(
        Studio,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    name = models.CharField(max_length=100)
    address = models.ForeignKey(
        "Address",
        on_delete=models.SET_NULL,
        related_name="locations",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=False)
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.studio.name} - {self.name}"


class Room(SoftDeletableModel, UUIDModel, TimeStampedModel):
    studio = models.ForeignKey(
        Studio,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class StudioSettings(TimeStampedModel):
    """Singleton studio-wide policy settings (pk forced to 1)."""

    free_cancellation_hours = models.PositiveIntegerField(
        default=2,
        help_text="Hours before class start when members can cancel for free.",
    )

    class Meta:
        verbose_name = "Studio settings"
        verbose_name_plural = "Studio settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "StudioSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Studio settings (free cancel: {self.free_cancellation_hours}h)"


class StudioBranding(TimeStampedModel):
    """White-label branding, one row per studio plus one default row.

    ``studio`` is NULL for the default row (used by the public site and as the
    fallback for studios that have not customized anything). A studio-specific
    row overrides it. Branding is therefore scoped per studio, ready for
    several studios under one platform.

    The logo is sanitized SVG text kept in the database (no file storage on
    the free tier). Colors are ``#RRGGBB`` and fonts come from an allowlist.
    """

    studio = models.OneToOneField(
        Studio,
        on_delete=models.CASCADE,
        related_name="branding",
        null=True,
        blank=True,
        help_text="Empty for the default branding.",
    )
    name = models.CharField(max_length=100, default="PulseFit Studio")
    tagline = models.CharField(max_length=140, blank=True, default="")
    logo_svg = models.TextField(blank=True, default="")
    primary_color = models.CharField(max_length=7, default="#4F46E5")
    secondary_color = models.CharField(max_length=7, default="#1F2937")
    background_color = models.CharField(max_length=7, default="#F8FAFC")
    text_color = models.CharField(max_length=7, default="#1F2937")
    heading_font = models.CharField(max_length=40, default="Rubik")
    body_font = models.CharField(max_length=40, default="Rubik")

    class Meta:
        verbose_name = "Studio branding"
        verbose_name_plural = "Studio branding"
        constraints = [
            models.UniqueConstraint(
                condition=models.Q(studio__isnull=True),
                fields=["studio"],
                name="studiobranding_single_default",
            )
        ]

    @classmethod
    def default_row(cls) -> "StudioBranding":
        obj = cls.objects.filter(studio__isnull=True).first()
        return obj or cls.objects.create(studio=None)

    @classmethod
    def load(cls, studio=None) -> "StudioBranding":
        """Branding for ``studio`` (created on first edit), or the default row."""
        if studio is None:
            return cls.default_row()
        obj = cls.objects.filter(studio=studio).first()
        return obj or cls.objects.create(studio=studio, name=studio.name)

    @classmethod
    def effective(cls, studio=None) -> "StudioBranding":
        """Read path: the studio's own row when it exists, else the default."""
        if studio is not None:
            obj = cls.objects.filter(studio=studio).first()
            if obj:
                return obj
        return cls.default_row()

    def __str__(self):
        return f"Branding: {self.name}"
