"""Real row-lock races. Skipped on SQLite, run in the PostgreSQL job."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta

import pytest
from django.db import close_old_connections, connection, transaction
from django.utils import timezone
from model_bakery import baker

from apps.members.members import cancel_reservation
from apps.members.models import Reservation
from apps.members.exceptions import ReservationInvalidStateException
from apps.wallets.models import ClassCreditLot, PlanPurchase, Wallet
from apps.wallets.services import WalletService
from apps.wallets.exceptions import InsufficientCreditsException, PurchaseAlreadyActivatedException

pytestmark = pytest.mark.django_db(transaction=True)


def race(fn):
    barrier = Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return fn()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        return [future.result(timeout=20) for future in futures]


def postgres_only():
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")


def test_concurrent_activation_grants_once(base_graph):
    postgres_only()
    member, _, _ = base_graph
    plan = baker.make("plans.Plan", classes_included=1, duration_days=30, guest_passes_included=0)
    purchase = PlanPurchase.objects.create(user=member.user, plan=plan, price_paid=0)

    def run():
        try:
            WalletService.activate_purchase(PlanPurchase.objects.get(pk=purchase.pk))
            return "activated"
        except PurchaseAlreadyActivatedException:
            return "already"

    assert sorted(race(run)) == ["activated", "already"]
    assert ClassCreditLot.objects.filter(purchase=purchase).count() == 1
    assert Wallet.objects.get(user=member.user).class_credits == 11


def test_two_debits_compete_for_one_credit(base_graph):
    postgres_only()
    member, _, room = base_graph
    Wallet.objects.filter(user=member.user).update(class_credits=0)
    plan = baker.make("plans.Plan", classes_included=1, duration_days=30, guest_passes_included=0)
    purchase = PlanPurchase.objects.create(user=member.user, plan=plan, price_paid=0)
    WalletService.activate_purchase(purchase)
    schedule = baker.make(
        "schedules.Schedule", room=room, start_time=timezone.now() + timedelta(hours=12)
    )

    def run():
        try:
            with transaction.atomic():
                reservation = baker.make(
                    Reservation, member=member, schedule=schedule, credit_charged=False
                )
                reservation.credit_charged = WalletService.consume_class_credit(
                    member.user, class_time=schedule.start_time, reservation=reservation
                )
                reservation.save()
            return "charged"
        except InsufficientCreditsException:
            return "insufficient"

    assert sorted(race(run)) == ["charged", "insufficient"]
    assert ClassCreditLot.objects.get(purchase=purchase).remaining == 0
    assert Wallet.objects.get(user=member.user).class_credits == 0
    assert Reservation.objects.filter(schedule=schedule, credit_charged=True).count() == 1


def test_concurrent_cancel_refunds_once(base_graph):
    postgres_only()
    member, _, room = base_graph
    plan = baker.make("plans.Plan", classes_included=1, duration_days=30, guest_passes_included=0)
    purchase = PlanPurchase.objects.create(user=member.user, plan=plan, price_paid=0)
    WalletService.activate_purchase(purchase)
    schedule = baker.make(
        "schedules.Schedule", room=room, start_time=timezone.now() + timedelta(hours=12)
    )
    reservation = baker.make(Reservation, member=member, schedule=schedule, credit_charged=False)
    with transaction.atomic():
        reservation.credit_charged = WalletService.consume_class_credit(
            member.user, class_time=schedule.start_time, reservation=reservation
        )
        reservation.save()

    def run():
        try:
            cancel_reservation(
                str(reservation.pk),
                bypass_free_cancel_window=True,
                promote_waitlist=False,
                notify=False,
            )
            return "cancelled"
        except ReservationInvalidStateException:
            return "already"

    assert sorted(race(run)) == ["already", "cancelled"]
    assert ClassCreditLot.objects.get(purchase=purchase).remaining == 1
    assert Wallet.objects.get(user=member.user).class_credits == 11
