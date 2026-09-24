"""Wallet payload embeds each purchase's plan benefits (CYC-82)."""

from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

from apps.plans.models import Benefit, Plan
from apps.wallets.models import PlanPurchase


@pytest.mark.django_db
def test_wallet_purchases_include_active_plan_benefits(user, wallet):
    priority = Benefit.objects.create(
        name="Priority booking", description="Book first", is_active=True
    )
    freeze = Benefit.objects.create(name="Freeze", description="", is_active=True)
    hidden = Benefit.objects.create(name="Old perk", description="", is_active=False)
    plans = []
    for i in range(3):
        plan = baker.make(Plan, name=f"Plan {i}", price=Decimal("10000"), is_active=True)
        plan.benefits.set([priority, freeze, hidden])
        plans.append(plan)
        PlanPurchase.objects.create(user=user, plan=plan, price_paid=Decimal("10000"))

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(reverse("wallet-list"))

    assert resp.status_code == 200
    purchases = resp.data["purchases"]
    assert len(purchases) == 3
    for row in purchases:
        assert row["plan_id"] == row["plan"]["id"]
        names = [b["name"] for b in row["plan"]["benefits_list"]]
        assert names == ["Freeze", "Priority booking"]


@pytest.mark.django_db
def test_wallet_benefit_queries_do_not_grow_with_purchases(user, wallet):
    benefit = Benefit.objects.create(name="Priority booking", description="", is_active=True)
    plan = baker.make(Plan, name="Plan", price=Decimal("10000"), is_active=True)
    plan.benefits.set([benefit])
    PlanPurchase.objects.create(user=user, plan=plan, price_paid=Decimal("10000"))

    client = APIClient()
    client.force_authenticate(user=user)
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as one:
        client.get(reverse("wallet-list"))
    for i in range(4):
        other = baker.make(Plan, name=f"P{i}", price=Decimal("1"), is_active=True)
        other.benefits.set([benefit])
        PlanPurchase.objects.create(user=user, plan=other, price_paid=Decimal("1"))
    with CaptureQueriesContext(connection) as five:
        client.get(reverse("wallet-list"))
    assert len(five) == len(one)
