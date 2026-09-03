"""Management command to deactivate expired unlimited memberships."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.wallets.models import Wallet


class Command(BaseCommand):
    help = "Deactivate unlimited memberships whose active_membership_end_date has passed."

    def handle(self, *args, **options):
        today = timezone.now().date()
        expired = Wallet.objects.filter(
            is_unlimited_membership_active=True,
            active_membership_end_date__lt=today,
        )
        count = expired.update(is_unlimited_membership_active=False)
        self.stdout.write(self.style.SUCCESS(f"Deactivated {count} expired membership(s)."))
