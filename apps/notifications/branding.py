"""Resolve the known event studio; never infer tenancy from a user's last booking."""

from apps.studios.services import get_studio_branding


def email_branding(studio=None):
    return get_studio_branding(getattr(studio, "pk", None))
