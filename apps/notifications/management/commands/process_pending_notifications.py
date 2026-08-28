"""Retry every notification stuck in "enqueued" status.

Intended to be run periodically (e.g. by a Render Cron Job) so failed sends
get retried even when no new notification is created afterwards to trigger
the opportunistic retry baked into ``create_notification``.
"""

from django.core.management.base import BaseCommand

from apps.notifications.services import flush_pending_notifications


class Command(BaseCommand):
    help = "Retry sending every notification currently in 'enqueued' status."

    def handle(self, *args, **options):
        count = flush_pending_notifications()
        self.stdout.write(self.style.SUCCESS(f"Processed {count} pending notification(s)."))
