"""Outbound purchase / wallet notifications."""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from django.conf import settings

from apps.notifications.email_templates import render_purchase_receipt
from apps.notifications.services import create_notification
from apps.plans import constants
from apps.wallets.models import PlanPurchase

logger = logging.getLogger(__name__)

_MONTHS_SHORT_ES = (
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
)

_PAYMENT_METHOD_LABELS = {
    constants.PAYMENT_METHOD_WEBPAY: "Webpay",
    constants.PAYMENT_METHOD_MERCADOPAGO: "Mercado Pago",
}


def _frontend_url() -> str:
    return (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip("/")


def purchase_folio(purchase: PlanPurchase) -> str:
    """Stable human-readable receipt id, e.g. PF-2026-08421."""
    year = purchase.created.year if purchase.created else 2026
    purchase_id = purchase.id
    if isinstance(purchase_id, str):
        purchase_id = UUID(purchase_id)
    n = int(purchase_id.hex[:8], 16) % 100_000
    return f"PF-{year}-{n:05d}"


def format_clp(amount) -> str:
    value = Decimal(str(amount or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    grouped = f"{int(value):,}".replace(",", ".")
    return f"${grouped} CLP"


def _format_until(end_date) -> str:
    if not end_date:
        return ""
    month = _MONTHS_SHORT_ES[end_date.month - 1]
    return f"{end_date.day} {month} {end_date.year}"


def _credits_label(plan, quantity: int) -> str:
    classes = plan.classes_included
    if classes is None:
        return "Ilimitadas"
    total = int(classes) * quantity
    noun = "clase" if total == 1 else "clases"
    return f"{total} {noun}"


def _validity_label(plan, quantity: int, end_date) -> str:
    days = plan.duration_days
    until = _format_until(end_date)
    if days is None:
        return until or "Sin vencimiento"
    total_days = int(days) * quantity
    noun = "día" if total_days == 1 else "días"
    if until:
        return f"{total_days} {noun} · hasta {until}"
    return f"{total_days} {noun}"


def _preheader(plan, quantity: int) -> str:
    classes = plan.classes_included
    days = plan.duration_days
    if classes is not None and days is not None:
        total = int(classes) * quantity
        total_days = int(days) * quantity
        noun = "crédito" if total == 1 else "créditos"
        return f"Pago recibido. {total} {noun} válidos {total_days} días desde hoy."
    if classes is not None:
        total = int(classes) * quantity
        noun = "crédito" if total == 1 else "créditos"
        return f"Pago recibido. {total} {noun} ya están en tu billetera."
    if days is not None:
        total_days = int(days) * quantity
        return f"Pago recibido. Vigente {total_days} días desde hoy."
    return "Pago recibido. Tu compra ya está activa en la billetera."


def send_purchase_receipt_email(purchase: PlanPurchase) -> None:
    """Send the purchase-receipt HTML email. Failures are logged, never raised."""
    try:
        purchase = PlanPurchase.objects.select_related("user", "plan").get(pk=purchase.pk)
        user = purchase.user
        plan = purchase.plan
        quantity = purchase.quantity or 1
        first_name = (user.first_name or "").strip()
        plan_name = (plan.name or "Plan").strip() or "Plan"
        amount_label = format_clp(purchase.price_paid)
        credits_label = _credits_label(plan, quantity)
        end_date = purchase.end.date() if purchase.end else None
        validity_label = _validity_label(plan, quantity, end_date)
        method_key = (purchase.payment_method or "").strip().lower()
        payment_method_label = _PAYMENT_METHOD_LABELS.get(method_key, "")
        folio = purchase_folio(purchase)

        frontend_url = _frontend_url()
        wallet_url = f"{frontend_url}/#wallet"
        subject = f"Comprobante · {plan_name} · {amount_label.replace(' CLP', '')}"
        preheader = _preheader(plan, quantity)
        message = (
            f"Pago recibido. {plan_name} · {amount_label}. "
            f"{credits_label}. Vigencia: {validity_label}. "
            f"Folio {folio}. Ver billetera: {wallet_url}"
        )

        create_notification(
            subject=subject,
            message=message,
            recipient_list=[user],
            html_content=render_purchase_receipt(
                first_name=first_name,
                plan_name=plan_name,
                amount_label=amount_label,
                credits_label=credits_label,
                validity_label=validity_label,
                payment_method_label=payment_method_label,
                folio=folio,
                wallet_url=wallet_url,
                frontend_url=frontend_url,
                preheader=preheader,
            ),
        )
    except Exception:
        logger.exception(
            "Failed to send purchase receipt email",
            extra={"purchase_id": str(getattr(purchase, "pk", ""))},
        )
