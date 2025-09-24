from django.contrib.auth import get_user_model

from apps.notifications import notifications
from apps.notifications.schemas import Notification as NotificationSchema
from apps.notifications.tasks import async_send_notifications

User = get_user_model()


def create_notification(subject: str, message: str, recipient_list: list[User]) -> None:
    """
    Creates and sends a notification to a list of recipients asynchronously.

    This function creates a notification with the given subject and message for
    a list of recipients. After creating the notification, it triggers an
    asynchronous task to send the notifications.

    Parameters:
    subject: str
        The subject of the notification.
    message: str
        The message content of the notification.
    recipient_list: list[User]
        A list of User objects representing the recipients of the
        notification.

    Returns:
    None
    """
    notifications.create_notification(subject, message, recipient_list)
    pending_notifications = get_pending_notifications()
    _notifications = [notification.model_dump() for notification in pending_notifications]
    async_send_notifications.delay(notifications=_notifications)


def get_pending_notifications() -> list[NotificationSchema]:
    """
    Fetch and transform pending notifications.

    Returns a list of notifications in the form of NotificationSchema objects that
    are currently pending. The function fetches pending notifications from the
    data storage and returns them after transforming them into the defined schema.

    Returns:
        list[NotificationSchema]: A list of NotificationSchema objects representing
        the pending notifications.
    """
    pending_notifications = notifications.get_pending_notifications()
    return [NotificationSchema(**notification) for notification in pending_notifications]
