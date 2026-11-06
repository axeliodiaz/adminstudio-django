from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import transaction
from django.utils import timezone
from model_bakery import baker

from apps.members.members import cancel_reservation
from apps.members.models import Reservation
from apps.plans.models import Plan
from apps.wallets.credit_balances import with_available_credits
from apps.wallets.exceptions import InsufficientCreditsException, PurchaseAlreadyActivatedException
from apps.wallets.models import ClassCreditLot, PlanPurchase, Wallet
from apps.wallets.schemas import WalletSchema
from apps.wallets.services import WalletService


def activate(user, days=30, classes=3, **kw):
    plan = baker.make(
        Plan, type="PACKAGE", duration_days=days, classes_included=classes, guest_passes_included=0
    )
    purchase = PlanPurchase.objects.create(user=user, plan=plan, price_paid=Decimal("0"), **kw)
    WalletService.activate_purchase(purchase)
    purchase.refresh_from_db()
    return purchase


def reservation(member, room):
    schedule = baker.make(
        "schedules.Schedule", room=room, start_time=timezone.now() + timedelta(hours=12)
    )
    return baker.make(Reservation, member=member, schedule=schedule, credit_charged=False)


def charge(r, when=None):
    with transaction.atomic():
        r.credit_charged = WalletService.consume_class_credit(
            r.member.user, class_time=when or r.schedule.start_time, reservation=r
        )
        r.save()


def test_existing_credits_never_backfilled_or_expired(base_graph):
    member, _, room = base_graph
    r = reservation(member, room)
    charge(r, timezone.now() + timedelta(days=3000))
    assert Wallet.objects.get(user=member.user).class_credits == 9
    assert not ClassCreditLot.objects.exists()
    assert r.credit_lot_id is None


def test_only_new_eligible_purchases_get_lots(base_graph):
    member, _, _ = base_graph
    p = activate(member.user, credit_expiry_enabled=False)
    assert not ClassCreditLot.objects.filter(purchase=p).exists()
    assert Wallet.objects.get(user=member.user).available_class_credits == 13


def test_snapshot_stays_when_plan_edited(base_graph):
    member, _, _ = base_graph
    p = activate(member.user)
    end = p.end
    Plan.objects.filter(pk=p.plan_id).update(duration_days=1)
    p.refresh_from_db()
    p.save()
    p.refresh_from_db()
    assert p.package_validity_days == 30
    assert p.end == end == p.credit_lot.expires_at


def test_unactivated_purchase_snapshots_validity_at_sale(base_graph):
    member, _, _ = base_graph
    plan = baker.make(Plan, type="PACKAGE", duration_days=30, classes_included=3)
    p = PlanPurchase.objects.create(user=member.user, plan=plan, price_paid=0)
    Plan.objects.filter(pk=plan.pk).update(duration_days=1)
    WalletService.activate_purchase(p)
    p.refresh_from_db()
    assert p.package_validity_days == 30
    assert timezone.localtime(p.end).date() == p.activated_since + timedelta(days=30)


def test_earliest_eligible_lot_first_then_legacy(base_graph):
    member, _, room = base_graph
    later = activate(member.user, days=30, classes=1)
    earlier = activate(member.user, days=2, classes=1)
    r = reservation(member, room)
    charge(r)
    assert r.credit_lot_id == earlier.credit_lot.id
    r2 = reservation(member, room)
    charge(r2)
    assert r2.credit_lot_id == later.credit_lot.id
    r3 = reservation(member, room)
    charge(r3)
    assert r3.credit_lot_id is None
    assert Wallet.objects.get(user=member.user).class_credits == 9


def test_class_time_not_booking_time(base_graph):
    member, _, room = base_graph
    wallet = Wallet.objects.get(user=member.user)
    wallet.class_credits = 0
    wallet.save()
    p = activate(member.user, days=1, classes=1)
    r = reservation(member, room)
    with pytest.raises(InsufficientCreditsException):
        charge(r, p.end + timedelta(microseconds=1))
    charge(r, p.end)
    assert r.credit_lot_id == p.credit_lot.id


def test_expired_read_is_lazy_and_balances_agree(base_graph):
    member, _, _ = base_graph
    p = activate(member.user)
    ClassCreditLot.objects.filter(purchase=p).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    wallet = Wallet.objects.get(user=member.user)
    assert wallet.class_credits == 13
    assert wallet.available_class_credits == 10
    assert WalletSchema.model_validate(wallet).class_credits == 10
    assert with_available_credits(Wallet.objects.all()).get(pk=wallet.pk).valid_class_credits == 10
    wallet.refresh_from_db()
    assert wallet.class_credits == 13


def test_member_cancellation_does_not_extend_expired_lot(base_graph):
    member, _, room = base_graph
    p = activate(member.user, classes=1)
    r = reservation(member, room)
    charge(r)
    expired = timezone.now() - timedelta(seconds=1)
    ClassCreditLot.objects.filter(purchase=p).update(expires_at=expired)
    cancel_reservation(str(r.id), bypass_free_cancel_window=True, promote_waitlist=False)
    p.credit_lot.refresh_from_db()
    assert p.credit_lot.remaining == 1
    assert p.credit_lot.expires_at == expired
    assert Wallet.objects.get(user=member.user).available_class_credits == 10


def test_cancel_refunds_once(base_graph):
    member, _, room = base_graph
    p = activate(member.user, classes=1)
    r = reservation(member, room)
    charge(r)
    cancel_reservation(str(r.id), bypass_free_cancel_window=True, promote_waitlist=False)
    with pytest.raises(Exception):
        cancel_reservation(str(r.id), bypass_free_cancel_window=True, promote_waitlist=False)
    assert Wallet.objects.get(user=member.user).class_credits == 11
    assert ClassCreditLot.objects.get(purchase=p).remaining == 1


def test_reactivation_never_grants_duplicate(base_graph):
    member, _, _ = base_graph
    p = activate(member.user)
    with pytest.raises(PurchaseAlreadyActivatedException):
        WalletService.activate_purchase(p)
    assert ClassCreditLot.objects.filter(purchase=p).count() == 1
    assert Wallet.objects.get(user=member.user).class_credits == 13


def test_old_charged_booking_refunds_after_later_unlimited_activation(base_graph):
    member, _, room = base_graph
    r = reservation(member, room)
    charge(r)
    Wallet.objects.filter(user=member.user).update(is_unlimited_membership_active=True)
    cancel_reservation(str(r.id), bypass_free_cancel_window=True, promote_waitlist=False)
    assert Wallet.objects.get(user=member.user).class_credits == 10


def test_unlimited_checked_at_class_date(base_graph):
    member, _, room = base_graph
    wallet = Wallet.objects.get(user=member.user)
    wallet.class_credits = 0
    wallet.is_unlimited_membership_active = True
    wallet.active_membership_end_date = timezone.localdate()
    wallet.save()
    r = reservation(member, room)
    with pytest.raises(InsufficientCreditsException):
        charge(r, timezone.now() + timedelta(days=2))


def test_replacement_policy_missing_rolls_back_cancel(base_graph):
    member, _, room = base_graph
    p = activate(member.user, classes=1)
    r = reservation(member, room)
    charge(r)
    ClassCreditLot.objects.filter(purchase=p).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    with pytest.raises(ValueError, match="policy is not configured"):
        cancel_reservation(
            str(r.id),
            bypass_free_cancel_window=True,
            cancellation_source="studio",
            promote_waitlist=False,
            notify=False,
        )
    r.refresh_from_db()
    assert r.credit_charged
    assert not ClassCreditLot.objects.filter(replacement_for=r).exists()


@pytest.mark.parametrize("days", [None, 7])
def test_replacement_policy_explicit_test_configuration(base_graph, settings, days):
    settings.CLASS_CREDIT_REPLACEMENT_VALIDITY_DAYS = days
    member, _, room = base_graph
    p = activate(member.user, classes=1)
    r = reservation(member, room)
    charge(r)
    ClassCreditLot.objects.filter(purchase=p).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    cancel_reservation(
        str(r.id),
        bypass_free_cancel_window=True,
        cancellation_source="studio",
        promote_waitlist=False,
        notify=False,
    )
    replacement = ClassCreditLot.objects.get(replacement_for=r)
    assert replacement.remaining == 1
    assert (replacement.expires_at is None) == (days is None)
    assert Wallet.objects.get(user=member.user).available_class_credits == 11
    assert ClassCreditLot.objects.get(purchase=p).remaining == 0


def test_faq_explains_class_time_legacy_and_studio_replacement():
    from apps.faqs.models import FAQItem

    row = FAQItem.objects.get(pk="b66c0979-3502-433f-af46-de18097178a5")
    assert row.is_published and not row.section.requires_staff
    assert "sin vencimiento" in row.answer
    assert "la clase debe comenzar" in row.answer
    assert "crédito de reemplazo" in row.answer


def test_failed_booking_rolls_back_both_lot_and_wallet(base_graph):
    member, _, room = base_graph
    p = activate(member.user, classes=1)
    r = reservation(member, room)
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            charge(r)
            raise RuntimeError("simulate reservation failure")
    assert ClassCreditLot.objects.get(purchase=p).remaining == 1
    assert Wallet.objects.get(user=member.user).class_credits == 11


def test_membership_credits_outside_package_policy(base_graph):
    member, _, _ = base_graph
    plan = baker.make(Plan, type="MEMBERSHIP", duration_days=30, classes_included=3)
    p = PlanPurchase.objects.create(user=member.user, plan=plan, price_paid=0)
    WalletService.activate_purchase(p)
    p.refresh_from_db()
    assert not p.credit_expiry_enabled
    assert not ClassCreditLot.objects.filter(purchase=p).exists()
    assert Wallet.objects.get(user=member.user).available_class_credits == 13
