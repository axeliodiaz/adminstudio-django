import logging

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404

from apps.notifications.models import Notification
from apps.notifications.schemas import Notification as NotificationSchema
from apps.users.services import get_user_from_id

logger = logging.getLogger(__name__)


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

        send_mail(
            subject=notification.subject,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user["email"]],
            fail_silently=False,
        )
        logger.info(
            "Email sent",
            extra={
                "notification_id": str(notification.id),
                "user_id": str(notification.user_id),
                "subject": notification.subject,
                "recipient": user["email"],
            },
        )

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
