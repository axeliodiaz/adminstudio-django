import logging
from typing import Any

import resend
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
        return constants.MAIL_CLIENT_RESEND
        if settings.SENDGRID_API_KEY:
            return constants.MAIL_CLIENT_SENDGRID
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

    def send_mail(self):
        mailing_client = self.get_mailing_client()
        if mailing_client == constants.MAIL_CLIENT_SENDGRID:
            self.send_sendgrid_email()
        elif mailing_client == constants.MAIL_CLIENT_RESEND:
            self.send_resend_email()
        else:
            self.send_default_email()
        logger.info(
            "Email sent with %s",
            mailing_client,
            extra={
                "notification_id": str(self.notification_id),
                "subject": self.subject,
                "recipient_list": str(self.recipient_list),
                "from_email": str(self.from_email),
                "text_message": self.message,
                "html_content": self.html_content,
                "mailing_client": mailing_client,
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
