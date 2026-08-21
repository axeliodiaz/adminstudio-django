import pytest
from decimal import Decimal
from model_bakery import baker

from apps.plans.models import Benefit, Plan
from apps.wallets.models import PlanPurchase, Wallet
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
@pytest.mark.django_db
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
@pytest.mark.django_db
def wallet(user):
    """Create a wallet for a user."""
    return Wallet.objects.create(user=user)


@pytest.fixture
@pytest.mark.django_db
def plan():
    """Create a test plan."""
    return Plan.objects.create(
        name="Test Plan",
        type="MEMBERSHIP",
        price=99.99,
        duration_days=30,
        classes_included=10,
        guest_passes_included=2,
        is_active=True,
    )


@pytest.fixture
@pytest.mark.django_db
def plan_purchase(user, plan):
    """Create a plan purchase that is not yet activated."""
    return PlanPurchase.objects.create(
        user=user,
        plan=plan,
        price_paid=Decimal("99.99"),
        activated_since=None,
    )


@pytest.fixture
@pytest.mark.django_db
def activated_plan_purchase(user, plan):
    """Create an already activated plan purchase."""
    from django.utils import timezone

    purchase = PlanPurchase.objects.create(
        user=user,
        plan=plan,
        price_paid=Decimal("99.99"),
        activated_since=timezone.now().date(),
    )
    return purchase


@pytest.fixture
@pytest.mark.django_db
def benefit_priority_booking():
    """Create a priority booking benefit."""
    return Benefit.objects.create(
        name="Priority Booking",
        description="Priority booking benefit",
        is_active=True,
    )


@pytest.fixture
@pytest.mark.django_db
def benefit_freeze_membership():
    """Create a freeze membership benefit."""
    return Benefit.objects.create(
        name="Freeze Membership",
        description="Can freeze membership",
        is_active=True,
    )


@pytest.fixture
@pytest.mark.django_db
def benefit_founders_exclusive():
    """Create a founders exclusive benefit."""
    return Benefit.objects.create(
        name="Founders Exclusive",
        description="Founders exclusive benefit",
        is_active=True,
    )


@pytest.fixture
@pytest.mark.django_db
def benefit_unlimited_membership():
    """Create an unlimited membership benefit."""
    return Benefit.objects.create(
        name="Unlimited Membership",
        description="Unlimited membership benefit",
        is_active=True,
    )


@pytest.fixture
@pytest.mark.django_db
def plan_with_benefits(plan, benefit_priority_booking, benefit_freeze_membership):
    """Create a plan with benefits."""
    plan.benefits.set([benefit_priority_booking, benefit_freeze_membership])
    return plan
