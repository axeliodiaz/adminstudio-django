"""Membership/pack expiry reminder emails (CYC-6).

Emails members whose activated membership or class pack expires within the
configured window so they renew in time. No scheduler: run it daily from any
external trigger. Idempotent via PlanPurchase.expiry_reminder_sent_at.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.email_templates import render_membership_expiry
from apps.notifications.services import create_notification
from apps.plans import constants as plan_constants
from apps.wallets.models import PlanPurchase

DEFAULT_REMINDER_DAYS = 7

MONTHS_ES = [
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
]


def _cadence(days_left: int) -> str:
    if days_left == 0:
        return "vence hoy"
    if days_left == 1:
        return "caduca ma\u00f1ana"
    return f"caduca en {days_left} d\u00edas"


class Command(BaseCommand):
    help = "Email members whose activated membership/pack expires within the reminder window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=getattr(settings, "MEMBERSHIP_EXPIRY_REMINDER_DAYS", DEFAULT_REMINDER_DAYS),
            help="Days before expiry to send the reminder (default: setting or 7).",
        )

    def handle(self, *args, **options):
        days = max(int(options["days"]), 0)
        now = timezone.now()
        today = timezone.localdate()
        cutoff = now + timedelta(days=days)
        frontend_url = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip(
            "/"
        )
        action_url = f"{frontend_url}/#plans"
        purchases = (
            PlanPurchase.objects.filter(
                expiry_reminder_sent_at__isnull=True,
                end__gt=now,
                end__lte=cutoff,
                plan__type__in=[
                    plan_constants.PLAN_TYPE_MEMBERSHIP,
                    plan_constants.PLAN_TYPE_PACKAGE,
                ],
            )
            .exclude(user__email="")
            .select_related("plan", "user", "user__wallet")
        )
        sent = 0
        for purchase in purchases:
            user = purchase.user
            end_local = timezone.localtime(purchase.end)
            days_left = max((end_local.date() - today).days, 0)
            wallet = getattr(user, "wallet", None)
            remaining = wallet.class_credits if wallet else None
            total = purchase.plan.classes_included
            cadence = _cadence(days_left)
            subject = f"Tu {purchase.plan.name} {cadence}"
            message = f"Tu plan {purchase.plan.name} {cadence}."
            if total:
                message += f" Te quedan {remaining or 0} clases de este ciclo."
            message += " Renueva desde Planes y Membres\u00edas para no perder tu prioridad en lista de espera."
            end_date_label = f"{end_local.day} {MONTHS_ES[end_local.month - 1]} {end_local.year}"
            create_notification(
                subject,
                message,
                [user],
                html_content=render_membership_expiry(
                    plan_name=purchase.plan.name,
                    days_left=days_left,
                    end_date_label=end_date_label,
                    remaining_classes=remaining,
                    total_classes=total,
                    action_url=action_url,
                    frontend_url=frontend_url,
                ),
            )
            purchase.expiry_reminder_sent_at = now
            purchase.save(update_fields=["expiry_reminder_sent_at", "modified"])
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Membership expiry reminders sent: {sent}"))
