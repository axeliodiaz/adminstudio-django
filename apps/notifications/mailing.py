import logging
from typing import Any

import resend
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from sendgrid import Mail, SendGridAPIClient

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
        Determines and returns the mailing client based on available API keys.

        The method checks the settings for specific API keys in a precedence order
        to determine which mailing client to use. If no specific API keys are found,
        it falls back to a default mailing client.

        Returns:
            str: The identifier for the selected mailing client.
        """
        if getattr(settings, "SENDGRID_API_KEY", None):
            return constants.MAIL_CLIENT_SENDGRID
        if getattr(settings, "RESEND_API_KEY", None):
            return constants.MAIL_CLIENT_RESEND
        return constants.MAIL_CLIENT_DEFAULT

    def send_sendgrid_email(self, **kwargs: Any) -> Any | None:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=self.from_email,
            to_emails=self.recipient_list,  # list | str
            subject=self.subject,
            html_content=self.html_content or None,
            plain_text_content=self.message,
        )
        try:
            response = sg.send(message)
            return response
        except Exception as e:
            if hasattr(e, "body"):
                logger.error("SendGrid error body: %s", e.body)
            logger.exception("SendGrid exception")
            return None

    def send_resend_email(self, **kwargs: Any) -> Any | None:
        resend.api_key = settings.RESEND_API_KEY
        params = {
            "from": self.from_email,
            "to": self.recipient_list,
            "subject": self.subject,
            "html": self.html_content,
            "text": self.message,
        }
        email = resend.Emails.send(params)
        logger.info(email)

    def send_default_email(self):
        send_mail(
            subject=self.subject,
            message=self.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=self.recipient_list,
            fail_silently=False,
        )

    def _get_api_key_for_provider(self, provider: str) -> str | None:
        if provider == constants.MAIL_CLIENT_SENDGRID:
            return settings.SENDGRID_API_KEY
        if provider == constants.MAIL_CLIENT_RESEND:
            return settings.RESEND_API_KEY
        return None

    def send_mail(self):
        """
        Send email by proxying to external mailing service API via HTTP POST.

        As required, this issues a POST to constants.PYTHON_MAILING_URL
        with a JSON body containing: provider, subject, message, recipient_list,
        from_email, api_key, and optionally html_content.
        """
        mailing_client = self.get_mailing_client()
        # HTTP request payload (includes 'message' key as required by the API)
        request_payload = {
            "provider": mailing_client,
            "subject": self.subject,
            "message": self.message,
            "recipient_list": self.recipient_list,
            "from_email": self.from_email,
            "api_key": self._get_api_key_for_provider(mailing_client),
            "html_content": self.html_content if self.html_content else None,
        }
        # Logging payload must not contain reserved LogRecord attribute names like 'message'
        log_base = {
            "notification_id": str(self.notification_id),
            "subject": self.subject,
            "recipient_list": str(self.recipient_list),
            "from_email": str(self.from_email),
            "mailing_client": mailing_client,
        }

        try:
            resp = requests.post(
                constants.PYTHON_MAILING_URL,
                json=request_payload,
                timeout=20,
            )
            resp.raise_for_status()
        except Exception as e:
            logger.exception(
                "Failed to send email via external service",
                extra={**log_base, "error": str(e)},
            )
            # As a fallback, try existing mechanisms to avoid losing the email completely
            if mailing_client == constants.MAIL_CLIENT_SENDGRID:
                self.send_sendgrid_email()
            elif mailing_client == constants.MAIL_CLIENT_RESEND:
                self.send_resend_email()
            else:
                self.send_default_email()
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
