import logging
from typing import Any

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404

from apps.notifications import constants
from apps.notifications.models import Notification
from apps.notifications.schemas import Notification as NotificationSchema
from apps.users.services import get_user_from_id

logger = logging.getLogger(__name__)


class Email:
    def __init__(
        self,
        notification_id: str,
        subject: str,
        message: str,
        recipient_list: list[str],
        from_email: str = None,
        html_content: str = None,
        **kwargs: Any,
    ):
        self.notification_id = notification_id
        self.subject = subject
        self.message = message
        domain = getattr(settings, "EMAIL_DOMAIN", "pulsefit.com") or "pulsefit.com"
        self.from_email = from_email or settings.DEFAULT_FROM_EMAIL or f"noreply@{domain}"
        self.recipient_list = recipient_list
        self.html_content = html_content

    def _mailtrap_is_configured(self) -> bool:
        email_host = getattr(settings, "EMAIL_HOST", "") or ""
        email_user = getattr(settings, "EMAIL_HOST_USER", None)
        email_password = getattr(settings, "EMAIL_HOST_PASSWORD", None)
        smtp_ok = "mailtrap" in email_host.lower() and email_user and email_password
        return bool(smtp_ok or getattr(settings, "MAILTRAP_API_KEY", None))

    def get_mailing_client(self) -> str:
        """Pick a provider. Local (DEBUG) prefers Mailtrap; prod prefers Resend."""
        if getattr(settings, "DEBUG", False) and self._mailtrap_is_configured():
            return constants.MAIL_CLIENT_MAILTRAP
        if getattr(settings, "RESEND_API_KEY", None):
            return constants.MAIL_CLIENT_RESEND
        if self._mailtrap_is_configured():
            return constants.MAIL_CLIENT_MAILTRAP
        return constants.MAIL_CLIENT_DEFAULT

    def _mailtrap_from(self) -> dict:
        if not self.from_email:
            raise ValueError("from_email is required")
        raw = self.from_email.strip()
        if "<" in raw and raw.endswith(">"):
            name, rest = raw.split("<", 1)
            return {"name": name.strip().strip('"'), "email": rest[:-1].strip()}
        return {"email": raw}

    def _mailtrap_api_url(self) -> str:
        use_sandbox = getattr(settings, "MAILTRAP_USE_SANDBOX", False)
        inbox_id = getattr(settings, "MAILTRAP_INBOX_ID", None)
        if use_sandbox and inbox_id:
            return f"{constants.MAILTRAP_SANDBOX_API_URL}/{inbox_id}"
        return constants.MAILTRAP_API_URL

    def _send_via_mailtrap(self) -> None:
        api_key = settings.MAILTRAP_API_KEY
        payload = {
            "from": self._mailtrap_from(),
            "to": [{"email": address} for address in self.recipient_list],
            "subject": self.subject,
            "text": self.message,
        }
        if self.html_content:
            payload["html"] = self.html_content
        resp = requests.post(
            self._mailtrap_api_url(),
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        resp.raise_for_status()

    def _send_via_resend(self) -> requests.Response:
        payload = {
            "from": self.from_email,
            "to": self.recipient_list,
            "subject": self.subject,
            "text": self.message,
        }
        if self.html_content:
            payload["html"] = self.html_content
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }
        if self.notification_id:
            headers["Idempotency-Key"] = str(self.notification_id)
        resp = requests.post(
            constants.RESEND_API_URL,
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp

    def _send_via_python_mailing(self, mailing_client: str) -> requests.Response:
        request_payload = {
            "provider": mailing_client,
            "subject": self.subject,
            "message": self.message,
            "recipient_list": self.recipient_list,
            "from_email": self.from_email,
            "api_key": self._get_api_key_for_provider(mailing_client),
            "html_content": self.html_content if self.html_content else None,
        }
        resp = requests.post(
            constants.PYTHON_MAILING_URL,
            json=request_payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp

    def _get_api_key_for_provider(self, provider: str) -> str | None:
        if provider == constants.MAIL_CLIENT_RESEND:
            return settings.RESEND_API_KEY
        if provider == constants.MAIL_CLIENT_MAILTRAP:
            return settings.MAILTRAP_API_KEY
        return None

    def send_mail(self) -> bool:
        """
        Send email using the appropriate mailing client.

        For Mailtrap, sends via the Mailtrap HTTP API.
        For Resend, sends directly to the Resend HTTP API.
        For the default client, proxies to the external mailing service API via HTTP POST.

        Returns:
            bool: True if the email was actually sent (or handed off successfully) to the
            provider, False if the send was skipped or failed. Callers must not mark the
            related notification as sent unless this returns True, so failed sends are
            retried instead of silently lost.
        """
        mailing_client = self.get_mailing_client()
        log_base = {
            "notification_id": str(self.notification_id),
            "mailing_client": mailing_client,
            "recipient_count": len(self.recipient_list),
        }
        logger.info("Email send started", extra=log_base)

        if mailing_client == constants.MAIL_CLIENT_MAILTRAP:
            if not (self.from_email or "").strip():
                logger.warning(
                    "Skipping Mailtrap send because from_email is missing",
                    extra=log_base,
                )
                return False
            try:
                self._send_via_mailtrap()
            except Exception:
                logger.exception("Failed to send email via Mailtrap", extra=log_base)
                raise
            logger.info(
                "Email sent successfully via Mailtrap",
                extra=log_base,
            )
            return True

        try:
            if mailing_client == constants.MAIL_CLIENT_RESEND:
                resp = self._send_via_resend()
            else:
                resp = self._send_via_python_mailing(mailing_client)
        except requests.exceptions.RequestException as e:
            # Transient upstream failures (timeouts, 429/5xx) should not open a
            # Sentry issue per attempt (LoggingIntegration event_level=ERROR).
            logger.warning(
                "Failed to send email via external service",
                extra={**log_base, "error": str(e)},
            )
            # Don't raise - allow task to complete, but report failure so the
            # notification stays pending and gets retried later.
            return False
        except Exception as e:
            logger.exception(
                "Unexpected error sending email via external service",
                extra={**log_base, "error": str(e)},
            )
            # Don't raise - allow task to complete, but report failure so the
            # notification stays pending and gets retried later.
            return False
        logger.info(
            "Email request sent successfully via external service",
            extra={
                **log_base,
                "status_code": resp.status_code,
                "response_text": resp.text[:500],
            },
        )
        return True


def send_pending_emails(notifications: list[dict[str, str]]):
    """
    Sends all pending email notifications to their respective recipients.

    For each provided notification payload (id, subject, message, user_id):
    - fetch the recipient email via get_user_from_id
    - if email is present, send the email and mark the notification as sent
    """
    logger.info(
        "Starting to process pending email notifications", extra={"count": len(notifications)}
    )
    for notification_data in notifications:
        notification = NotificationSchema(**notification_data)
        logger.debug(
            "Processing notification",
            extra={"notification_id": str(notification.id), "user_id": str(notification.user_id)},
        )

        user = get_user_from_id(notification.user_id)
        if not user.get("email"):
            # Expected skip (users without email). Use warning so LoggingIntegration
            # (event_level=ERROR) does not open a Sentry issue.
            logger.warning(
                "Skipping notification because user has no email",
                extra={
                    "notification_id": str(notification.id),
                    "user_id": str(notification.user_id),
                },
            )
            continue

        recipient_list = notification.get_recipient_mail_list()
        email = Email(
            notification_id=str(notification.id),
            subject=notification.subject,
            message=notification.message,
            recipient_list=recipient_list,
            html_content=notification.html_content or None,
        )
        if email.send_mail():
            mark_notification_as_sent(str(notification.id))
        else:
            # Leave the notification as pending so it gets retried on the next call.
            logger.info(
                "Notification left pending for retry after send failure",
                extra={"notification_id": str(notification.id)},
            )


def mark_notification_as_sent(notification_uuid: str) -> None:
    """
    Marks a notification as sent by updating its status in the database.
    """
    notification = get_object_or_404(Notification, id=notification_uuid)
    notification.status = Notification.STATUS.sent
    notification.save(update_fields=["status"])
    logger.debug(
        "Notification marked as sent",
        extra={"notification_id": str(notification.id)},
    )
