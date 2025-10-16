from celery import shared_task

from apps.notifications.mailing import send_pending_emails


@shared_task
def async_send_notifications(notifications):
    """
    Asynchronous task for sending notifications.

    This function triggers the sending of pending email notifications
    as a background task.

    Raises:
        None: This function does not explicitly raise errors.
    """
    send_pending_emails(notifications)
