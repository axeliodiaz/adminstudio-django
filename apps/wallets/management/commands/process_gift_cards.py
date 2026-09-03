from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.wallets.models import GiftCard
from apps.wallets.notifications import (
    send_gift_expiration_reminder_email,
    send_gift_recipient_email,
)


class Command(BaseCommand):
    help = "Deliver scheduled gift cards, remind recipients, and expire unused cards."

    def handle(self, *args, **options):
        now = timezone.now()
        pending_delivery = GiftCard.objects.filter(
            status=GiftCard.Status.ACTIVE,
            delivered_at__isnull=True,
        ).filter(Q(send_at__isnull=True) | Q(send_at__lte=now))
        for gift_card in pending_delivery.select_related("plan", "issuer"):
            send_gift_recipient_email(gift_card)

        reminder_days = getattr(settings, "GIFT_CARD_REMINDER_DAYS", 7)
        reminder_cutoff = now + timedelta(days=reminder_days)
        pending_reminders = GiftCard.objects.filter(
            status=GiftCard.Status.ACTIVE,
            delivered_at__isnull=False,
            expiration_reminder_sent_at__isnull=True,
            expires_at__gt=now,
            expires_at__lte=reminder_cutoff,
        )
        for gift_card in pending_reminders.select_related("plan", "issuer"):
            send_gift_expiration_reminder_email(gift_card)

        expired = GiftCard.objects.filter(
            status=GiftCard.Status.ACTIVE,
            expires_at__lte=now,
        ).update(status=GiftCard.Status.EXPIRED, modified=now)
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed gifts: delivery={pending_delivery.count()}, "
                f"reminders={pending_reminders.count()}, expired={expired}"
            )
        )
