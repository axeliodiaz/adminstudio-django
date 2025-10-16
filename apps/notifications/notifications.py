from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from model_utils.models import SoftDeletableModel

from apps.notifications.models import Notification

User = get_user_model()


def create_notification(subject: str, message: str, recipient_list: list[User]) -> None:
    """
    Creates and sends notifications to a list of recipients.

    This function generates notifications for each user in the recipient list,
    saves them to the database in bulk, and triggers asynchronous sending
    of those notifications.

    Arguments:
        subject: The subject of the notification.
        message: The message content of the notification.
        recipient_list: A list of User objects representing the recipients
                        of the notification.

    Returns:
        None
    """
    notifications = [
        Notification(user=recipient, subject=subject, message=message)
        for recipient in recipient_list
    ]
    Notification.objects.bulk_create(notifications)


def get_pending_notifications() -> QuerySet[SoftDeletableModel, dict[str, Any]]:
    """
    Fetches pending notifications.

    This function retrieves all notifications that have a status of "enqueued" from the
    Notification model and returns them as a queryset of dictionary objects.

    Returns:
        QuerySet[SoftDeletableModel, dict[str, Any]]: A queryset containing the pending
        notifications with their details as dictionary objects.
    """
    return Notification.objects.filter(status=Notification.STATUS.enqueued).values()


def mark_notification_as_sent(notification_uuid: str) -> None:
    """
    Marks a notification as sent by updating its status.

    This function retrieves a `Notification` object, identified by its UUID, and updates
    its `status` to "sent" in the database. It ensures that only the relevant fields are
    saved to the database.

    Args:
        notification_uuid: The unique identifier of the notification to be marked as sent.

    Returns:
        None
    """
    notification = get_object_or_404(Notification, id=notification_uuid)
    notification.status = Notification.STATUS.sent
    notification.save(update_fields=["status"])
