"""Token authentication that does not write SQLite on every request."""

from django.db import transaction
from django.utils import timezone
from drf_expiring_token.authentication import (
    ExpiringTokenAuthentication as BaseExpiringTokenAuthentication,
)
from drf_expiring_token.authentication import token_expire_handler
from drf_expiring_token.models import ExpiringToken
from drf_expiring_token.settings import custom_settings
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(BaseExpiringTokenAuthentication):
    """Sliding expiry without a `token.save()` on each API call.

    The upstream class updates `expires` on every authenticate. Admin pages
    fire parallel GETs (Horarios loads instructors, rooms, and schedules at
    once). On SQLite that write contention raises OperationalError
    "database is locked" and the client shows HTTP 500.
    """

    @transaction.atomic(savepoint=False)
    def authenticate_credentials(self, key):
        try:
            token = ExpiringToken.objects.select_related("user").get(key=key)
        except ExpiringToken.DoesNotExist:
            raise AuthenticationFailed("Invalid Token")

        if not token.user.is_active:
            raise AuthenticationFailed("User is not active")

        is_expired, token = token_expire_handler(token)
        if is_expired:
            raise AuthenticationFailed("The Token is expired")

        duration = custom_settings.EXPIRING_TOKEN_DURATION
        remaining = token.expires - timezone.now()
        if remaining <= duration / 2:
            token.expires = timezone.now() + duration
            token.save(update_fields=["expires"])

        return token.user, token
