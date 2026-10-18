"""Event-driven freshness for the precomputed report tables (CYC-440).

A failed recompute must never break the write that triggered it (a booking
matters more than a report), so every handler swallows and logs errors; the
deploy-time ``refresh_reports`` and the manual refresh endpoint heal drift.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.coach.models import ClassRating
from apps.communications.models import TrackedLinkClick
from apps.members.models import Member, Reservation, WaitlistEntry
from apps.notifications.models import Notification
from apps.referrals.models import Referral
from apps.reports import services
from apps.schedules.models import Schedule
from apps.wallets.models import GiftCard, GuestPassInvitation, PlanPurchase

logger = logging.getLogger(__name__)


def _safe(fn, *args):
    try:
        fn(*args)
    except Exception:  # noqa: BLE001 - reporting must never break the source write
        logger.exception("reports recompute failed", extra={"args": [str(a) for a in args]})


def _classes_days(*days):
    for day in {day for day in days if day}:
        _safe(services.recompute_day_classes, day)


def _commercial_days(*days):
    for day in {day for day in days if day}:
        _safe(services.recompute_day_commercial, day)


@receiver(post_save, sender=Schedule, dispatch_uid="reports_schedule_saved")
def schedule_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _classes_days(services.local_date(instance.start_time))


@receiver(post_save, sender=Reservation, dispatch_uid="reports_reservation_saved")
def reservation_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _classes_days(services.local_date(instance.schedule.start_time))


@receiver(post_save, sender=WaitlistEntry, dispatch_uid="reports_waitlist_saved")
def waitlist_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _classes_days(
        services.local_date(instance.created),
        services.local_date(instance.schedule.start_time),
    )


@receiver(post_save, sender=ClassRating, dispatch_uid="reports_rating_saved")
def rating_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _classes_days(services.local_date(instance.schedule.start_time))


@receiver(post_save, sender=PlanPurchase, dispatch_uid="reports_purchase_saved")
def purchase_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _commercial_days(services.local_date(instance.created))


@receiver(post_save, sender=GiftCard, dispatch_uid="reports_giftcard_saved")
def giftcard_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _commercial_days(
        services.local_date(instance.created),
        services.local_date(instance.redeemed_at) if instance.redeemed_at else None,
    )


@receiver(post_save, sender=GuestPassInvitation, dispatch_uid="reports_guestpass_saved")
def guestpass_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    attended_at = instance.reservation.attended_at if instance.reservation_id else None
    _commercial_days(
        services.local_date(instance.created),
        services.local_date(instance.claimed_at) if instance.claimed_at else None,
        services.local_date(attended_at) if attended_at else None,
    )


@receiver(post_save, sender=Referral, dispatch_uid="reports_referral_saved")
def referral_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _commercial_days(
        services.local_date(instance.signed_up_at),
        services.local_date(instance.converted_at) if instance.converted_at else None,
    )


@receiver(post_save, sender=Notification, dispatch_uid="reports_notification_saved")
def notification_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _commercial_days(services.local_date(instance.created))


@receiver(post_save, sender=TrackedLinkClick, dispatch_uid="reports_click_saved")
def click_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _commercial_days(services.local_date(instance.created))


@receiver(post_save, sender=Member, dispatch_uid="reports_member_saved")
def member_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _commercial_days(services.local_date(instance.created))
