import hmac
import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.services import flush_pending_notifications


class FlushPendingNotificationsView(APIView):
    """Internal endpoint that retries every 'enqueued' notification.

    Meant to be called by a scheduled job (e.g. a Render Cron Job) rather
    than by end users, since the Render free plan cannot run a Docker-based
    cron job with direct DB access. Authenticated via a shared secret header
    instead of user auth so the cron job doesn't need any app credentials.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        expected_token = (os.environ.get("NOTIFICATIONS_CRON_TOKEN") or "").strip()
        if not expected_token:
            return Response(
                {"detail": "NOTIFICATIONS_CRON_TOKEN is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        provided_token = request.headers.get("X-Cron-Token", "")
        if not hmac.compare_digest(provided_token, expected_token):
            return Response({"detail": "Invalid token."}, status=status.HTTP_401_UNAUTHORIZED)

        processed = flush_pending_notifications()
        return Response({"processed": processed}, status=status.HTTP_200_OK)
