from django.contrib.auth import get_user_model

from apps.notifications import notifications
from apps.notifications.mailing import send_pending_emails
from apps.notifications.schemas import Notification as NotificationSchema
from apps.users.schemas import UserSchema
from apps.users.services import get_user_from_id

User = get_user_model()


def create_notification(subject: str, message: str, recipient_list: list[User]) -> None:
    """
    Creates a notification for each recipient and sends pending emails.

    Parameters:
    subject: str
        The subject of the notification.
    message: str
        The message content of the notification.
    recipient_list: list[User]
        A list of User objects representing the recipients of the
        notification.
    """
    notifications.create_notification(subject, message, recipient_list)
    pending_notifications = get_pending_notifications()
    send_pending_emails([notification.model_dump() for notification in pending_notifications])


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
    notifications_list = []
    for notification in pending_notifications:
        user = get_user_from_id(notification["user_id"])
        notification["recipient_list"] = [UserSchema(**user).model_dump()]
        notifications_list.append(NotificationSchema(**notification))
    return notifications_list
