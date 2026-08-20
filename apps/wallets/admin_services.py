"""Admin list helpers for wallets and plan purchases."""

from datetime import datetime, time

from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.analytics.constants import DEMO_PLAN_PREFIX
from apps.wallets.models import PlanPurchase, Wallet


def _display_name(user) -> str:
    name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
    return name or user.username or user.email or "Sin nombre"


def _plan_label(name: str | None) -> str | None:
    if not name:
        return None
    if name.startswith(DEMO_PLAN_PREFIX):
        return name[len(DEMO_PLAN_PREFIX) :]
    return name


def _active_plan_name(user, today) -> str | None:
    now = timezone.make_aware(datetime.combine(today, time.max))
    for purchase in user.plan_purchases.all():
        if purchase.activated_since is None:
            continue
        if purchase.end and purchase.end < now:
            continue
        return _plan_label(purchase.plan.name)
    return None


def list_admin_wallets(*, search: str | None = None, status: str | None = None) -> list[dict]:
    """Return wallets for the staff admin list."""
    today = timezone.localdate()
    queryset = (
        Wallet.objects.select_related("user")
        .prefetch_related(
            Prefetch(
                "user__plan_purchases",
                queryset=PlanPurchase.objects.select_related("plan").order_by("-created"),
            )
        )
        .order_by("user__first_name", "user__last_name", "user__email")
    )

    if status == "active":
        queryset = queryset.filter(
            Q(is_unlimited_membership_active=True) | Q(active_membership_end_date__gte=today)
        )
    elif status == "expired":
        queryset = queryset.filter(is_unlimited_membership_active=False).filter(
            Q(active_membership_end_date__isnull=True) | Q(active_membership_end_date__lt=today)
        )

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(user__first_name__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(user__email__icontains=term)
            | Q(user__username__icontains=term)
        )

    rows = []
    for wallet in queryset:
        user = wallet.user
        rows.append(
            {
                "id": str(wallet.id),
                "user_id": str(user.id),
                "user_name": _display_name(user),
                "user_email": user.email,
                "plan_name": _active_plan_name(user, today) or "—",
                "class_credits": wallet.class_credits,
                "guest_pass_credits": wallet.guest_pass_credits,
                "membership_end": (
                    wallet.active_membership_end_date.isoformat()
                    if wallet.active_membership_end_date
                    else None
                ),
                "is_unlimited": wallet.is_unlimited_membership_active,
                "is_priority": wallet.is_priority_booker,
                "can_freeze": wallet.can_freeze_membership,
                "is_founders": wallet.is_founders_exclusive,
                "retail_discount_percentage": float(wallet.retail_discount_percentage or 0),
                "created": wallet.created.isoformat() if wallet.created else None,
            }
        )
    return rows


def list_admin_purchases(*, search: str | None = None, plan_type: str | None = None) -> list[dict]:
    """Return plan purchases for the staff admin list."""
    queryset = PlanPurchase.objects.select_related("user", "plan").order_by("-created")

    if plan_type in {"MEMBERSHIP", "PACKAGE"}:
        queryset = queryset.filter(plan__type=plan_type)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(user__first_name__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(user__email__icontains=term)
            | Q(user__username__icontains=term)
            | Q(plan__name__icontains=term)
        )

    rows = []
    for purchase in queryset[:500]:
        user = purchase.user
        rows.append(
            {
                "id": str(purchase.id),
                "user_id": str(user.id),
                "user_name": _display_name(user),
                "user_email": user.email,
                "plan_id": str(purchase.plan_id),
                "plan_name": _plan_label(purchase.plan.name),
                "type": purchase.plan.type,
                "price_paid": float(purchase.price_paid or 0),
                "activated_since": (
                    purchase.activated_since.isoformat() if purchase.activated_since else None
                ),
                "start": purchase.start.isoformat() if purchase.start else None,
                "end": purchase.end.isoformat() if purchase.end else None,
                "created": purchase.created.isoformat() if purchase.created else None,
            }
        )
    return rows
