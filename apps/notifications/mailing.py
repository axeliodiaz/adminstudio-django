import logging
from typing import Any

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
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
        self.from_email = from_email or settings.DEFAULT_FROM_EMAIL
        self.recipient_list = recipient_list
        self.html_content = html_content

    def get_mailing_client(self) -> str:
        """
        Determines and returns the mailing client based on available API keys and SMTP configuration.

        Priority order:
        1. Mailtrap (if configured via SMTP or API key) - preferred for development/testing
        2. SendGrid (if API key is present)
        3. Resend (if API key is present)
        4. Default (external service)

        Returns:
            str: The identifier for the selected mailing client.
        """
        # Check Mailtrap first (preferred for development/testing)
        # Check if Mailtrap is configured via SMTP (as per Mailtrap documentation)
        email_host = getattr(settings, "EMAIL_HOST", "")
        email_user = getattr(settings, "EMAIL_HOST_USER", None)
        email_password = getattr(settings, "EMAIL_HOST_PASSWORD", None)
        if email_host and "mailtrap" in email_host.lower() and email_user and email_password:
            return constants.MAIL_CLIENT_MAILTRAP
        # Also check for MAILTRAP_API_KEY (for API mode, though we'll use SMTP)
        if getattr(settings, "MAILTRAP_API_KEY", None):
            return constants.MAIL_CLIENT_MAILTRAP

        # Then check other providers
        if getattr(settings, "SENDGRID_API_KEY", None):
            return constants.MAIL_CLIENT_SENDGRID
        if getattr(settings, "RESEND_API_KEY", None):
            return constants.MAIL_CLIENT_RESEND
        return constants.MAIL_CLIENT_DEFAULT

    def _get_api_key_for_provider(self, provider: str) -> str | None:
        if provider == constants.MAIL_CLIENT_SENDGRID:
            return settings.SENDGRID_API_KEY
        if provider == constants.MAIL_CLIENT_RESEND:
            return settings.RESEND_API_KEY
        if provider == constants.MAIL_CLIENT_MAILTRAP:
            return settings.MAILTRAP_API_KEY
        return None

    def send_mail(self):
        """
        Send email using the appropriate mailing client.

        For Mailtrap, sends directly via SMTP using Django's email backend (as per Mailtrap documentation).
        For other providers (SendGrid, Resend), proxies to external mailing service API via HTTP POST.
        """
        mailing_client = self.get_mailing_client()
        log_base = {
            "notification_id": str(self.notification_id),
            "mailing_client": mailing_client,
        }

        # Use SMTP directly for Mailtrap (as per Mailtrap Django documentation)
        if mailing_client == constants.MAIL_CLIENT_MAILTRAP:
            import time

            start_time = time.time()
            try:
                email = EmailMultiAlternatives(
                    subject=self.subject,
                    body=self.message,
                    from_email=self.from_email,
                    to=self.recipient_list,
                )
                if self.html_content:
                    email.attach_alternative(self.html_content, "text/html")
                email.send()
                elapsed_time = time.time() - start_time
                logger.info(
                    "Email sent successfully via Mailtrap SMTP",
                    extra={
                        **log_base,
                        "recipient_count": len(self.recipient_list),
                        "email_host": getattr(settings, "EMAIL_HOST", "N/A"),
                        "elapsed_seconds": round(elapsed_time, 2),
                    },
                )
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.exception(
                    "Failed to send email via Mailtrap SMTP",
                    extra={
                        **log_base,
                        "error": str(e),
                        "elapsed_seconds": round(elapsed_time, 2),
                    },
                )
                raise
        else:
            # Use external service for SendGrid, Resend, or default
            request_payload = {
                "provider": mailing_client,
                "subject": self.subject,
                "message": self.message,
                "recipient_list": self.recipient_list,
                "from_email": self.from_email,
                "api_key": self._get_api_key_for_provider(mailing_client),
                "html_content": self.html_content if self.html_content else None,
            }
            log_base["payload"] = request_payload

            try:
                # Increase timeout for external service to avoid ReadTimeout
                resp = requests.post(
                    constants.PYTHON_MAILING_URL,
                    json=request_payload,
                    timeout=60,  # Increased from 20 to 60 seconds
                )
                resp.raise_for_status()
            except requests.exceptions.Timeout as e:
                logger.error(
                    "Timeout sending email via external service - service may be slow or unavailable",
                    extra={
                        **log_base,
                        "error": str(e),
                        "timeout": 60,
                    },
                )
                # Don't raise - allow task to complete, email will be retried if needed
            except Exception as e:
                logger.exception(
                    "Failed to send email via external service",
                    extra={**log_base, "error": str(e)},
                )
                # Don't raise - allow task to complete
            else:
                logger.info(
                    "Email request sent successfully via external service",
                    extra={
                        **log_base,
                        "status_code": resp.status_code,
                        "response_text": resp.text[:500],
                    },
                )


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
            logger.error(
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
        )
        email.send_mail()
        mark_notification_as_sent(str(notification.id))


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
