"""Communications module models.

Currently only click tracking (CYC-396). Saved communications are CYC-393
(data model pending Axel's decision); when they land, a TrackedLink will
gain a nullable FK to the communication it belongs to.
"""

import secrets

from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel, UUIDModel


def generate_link_token():
    """Unguessable per-recipient token for tracked redirect URLs."""
    return secrets.token_urlsafe(24)


class TrackedLink(UUIDModel, TimeStampedModel):
    """A redirect URL with a per-recipient token (CYC-396).

    Links inside a communication are rewritten to ``/api/communications/r/<token>/``;
    each hit records who clicked (via the token), when and how many times,
    then redirects to ``target_url``.
    """

    token = models.CharField(max_length=64, unique=True, default=generate_link_token)
    target_url = models.URLField(max_length=1000)
    label = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="communications_tracked_links",
        help_text="Recipient this token was generated for.",
    )
    recipient_email = models.EmailField(
        blank=True,
        help_text="Snapshot of the recipient email at link creation time.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="communications_tracked_links_created",
    )
    is_active = models.BooleanField(default=True)
    click_count = models.PositiveIntegerField(default=0)
    first_clicked_at = models.DateTimeField(null=True, blank=True)
    last_clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.label or self.target_url} ({self.click_count} clicks)"


class TrackedLinkClick(UUIDModel, TimeStampedModel):
    """One click on a tracked link. Aggregates live on TrackedLink."""

    link = models.ForeignKey(TrackedLink, on_delete=models.CASCADE, related_name="clicks")
    user_agent = models.CharField(max_length=300, blank=True)
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 of the client IP; stored hashed, never raw.",
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Click on {self.link_id} at {self.created}"
