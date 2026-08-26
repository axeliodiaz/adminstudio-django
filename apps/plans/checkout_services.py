"""Checkout of one or more plans, with optional promo code."""

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

from apps.plans import constants
from apps.plans.models import Plan
from apps.plans.promo_services import compute_discount_amount, get_valid_promo_code
from apps.wallets.models import PlanPurchase
from apps.wallets.schemas import PlanPurchaseSchema
from apps.wallets.services import WalletService

TWOPLACES = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _serialize_purchase(purchase: PlanPurchase) -> dict:
    payload = {
        "id": purchase.id,
        "created": purchase.created,
        "modified": purchase.modified,
        "price_paid": purchase.price_paid,
        "activated_since": purchase.activated_since,
        "start": purchase.start,
        "end": purchase.end,
        "plan_id": purchase.plan.id,
        "plan_name": purchase.plan.name,
    }
    return PlanPurchaseSchema.model_validate(payload).model_dump(mode="json")


def checkout_plans(
    *,
    user,
    items: list[dict],
    promo_code: str | None = None,
    payment_method: str | None = None,
) -> dict:
    if not items:
        raise ValueError("El carrito está vacío.")

    method = (payment_method or "").strip().lower()
    if method and method not in {
        constants.PAYMENT_METHOD_MERCADOPAGO,
        constants.PAYMENT_METHOD_WEBPAY,
    }:
        raise ValueError("El método de pago no es válido.")

    resolved_items = []
    subtotal = Decimal("0.00")
    for item in items:
        quantity = int(item.get("quantity") or 1)
        if quantity < 1:
            raise ValueError("La cantidad debe ser al menos 1.")
        try:
            plan = Plan.objects.get(id=item["plan_id"], is_active=True)
        except Plan.DoesNotExist as exc:
            raise ValueError(f"No se encontró un plan activo con id {item['plan_id']}.") from exc
        unit_price = _quantize(Decimal(str(plan.price)))
        line_total = _quantize(unit_price * quantity)
        subtotal += line_total
        resolved_items.append(
            {
                "plan": plan,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    promo = None
    discount = Decimal("0.00")
    if promo_code:
        promo = get_valid_promo_code(promo_code)
        discount = compute_discount_amount(subtotal=subtotal, promo=promo)

    remaining_discount = discount
    purchases = []
    for index, item in enumerate(resolved_items):
        is_last = index == len(resolved_items) - 1
        if is_last:
            line_discount = remaining_discount
        elif subtotal > 0:
            line_discount = _quantize(discount * (item["line_total"] / subtotal))
            remaining_discount -= line_discount
        else:
            line_discount = Decimal("0.00")

        price_paid = _quantize(item["line_total"] - line_discount)
        if price_paid < 0:
            price_paid = Decimal("0.00")

        purchase = PlanPurchase.objects.create(
            user=user,
            plan=item["plan"],
            quantity=item["quantity"],
            price_paid=price_paid,
            discount_amount=line_discount,
            promo_code=promo,
            payment_method=method,
            activated_since=None,
        )
        if not settings.ENABLE_PSP_PAYMENTS:
            WalletService.activate_purchase(purchase)
        purchases.append(_serialize_purchase(purchase))

    return {
        "purchases": purchases,
        "subtotal": float(subtotal),
        "discount": float(discount),
        "total": float(_quantize(subtotal - discount)),
        "promo_code": promo.code if promo else None,
        "payment_method": method or None,
    }
