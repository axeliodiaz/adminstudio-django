from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.notifications.models import Notification
from apps.plans import constants as plan_constants
from apps.plans.models import Plan
from apps.wallets.models import PlanPurchase


def _activated_purchase(user, plan, *, days_left):
    return PlanPurchase.objects.create(
        user=user,
        plan=plan,
        price_paid=Decimal("99.99"),
        activated_since=timezone.localdate() - timedelta(days=plan.duration_days - days_left),
    )


@pytest.mark.django_db
def test_reminder_goes_out_within_window(user, wallet, plan):
    purchase = _activated_purchase(user, plan, days_left=5)
    wallet.class_credits = 2
    wallet.save()

    call_command("send_membership_expiry_reminders")

    purchase.refresh_from_db()
    assert purchase.expiry_reminder_sent_at is not None
    notification = Notification.objects.get(user=user)
    assert notification.subject == f"Tu {plan.name} caduca en 5 d\u00edas"
    assert "Renovar plan" in notification.html_content
    assert "2 de 10" in notification.html_content
    assert "lista de espera" in notification.html_content


@pytest.mark.django_db
def test_command_is_idempotent(user, wallet, plan):
    purchase = _activated_purchase(user, plan, days_left=5)

    call_command("send_membership_expiry_reminders")
    call_command("send_membership_expiry_reminders")

    assert Notification.objects.filter(user=user).count() == 1
    purchase.refresh_from_db()
    assert purchase.expiry_reminder_sent_at is not None


@pytest.mark.django_db
def test_outside_window_is_skipped(user, wallet, plan):
    purchase = _activated_purchase(user, plan, days_left=20)

    call_command("send_membership_expiry_reminders")

    purchase.refresh_from_db()
    assert purchase.expiry_reminder_sent_at is None
    assert not Notification.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_days_argument_widens_window(user, wallet, plan):
    purchase = _activated_purchase(user, plan, days_left=20)

    call_command("send_membership_expiry_reminders", days=25)

    purchase.refresh_from_db()
    assert purchase.expiry_reminder_sent_at is not None


@pytest.mark.django_db
def test_unactivated_purchase_is_skipped(user, plan_purchase):
    call_command("send_membership_expiry_reminders")

    plan_purchase.refresh_from_db()
    assert plan_purchase.expiry_reminder_sent_at is None
    assert not Notification.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_gift_card_plan_is_skipped(user, wallet):
    gift_plan = Plan.objects.create(
        name="Gift 4",
        type=plan_constants.PLAN_TYPE_GIFT_CARD,
        price=50.0,
        duration_days=30,
        classes_included=4,
        is_active=True,
    )
    purchase = _activated_purchase(user, gift_plan, days_left=5)

    call_command("send_membership_expiry_reminders")

    purchase.refresh_from_db()
    assert purchase.expiry_reminder_sent_at is None
    assert not Notification.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_expired_purchase_is_skipped(user, wallet, plan):
    purchase = PlanPurchase.objects.create(
        user=user,
        plan=plan,
        price_paid=Decimal("99.99"),
        activated_since=timezone.localdate() - timedelta(days=plan.duration_days + 1),
    )

    call_command("send_membership_expiry_reminders")

    purchase.refresh_from_db()
    assert purchase.expiry_reminder_sent_at is None
    assert not Notification.objects.filter(user=user).exists()
