"""Checkout of one or more plans, with optional promo code."""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.plans import constants
from apps.plans.models import Plan
from apps.plans.promo_services import compute_discount_amount, get_valid_promo_code
from apps.wallets.models import GiftCard, PlanPurchase
from apps.wallets.notifications import send_gift_purchase_receipt_email, send_gift_recipient_email
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
    gift_recipient: dict | None = None,
) -> dict:
    if not items:
        raise ValueError("El carrito está vacío.")

    # Lock the account while we evaluate introductory-plan eligibility so two
    # concurrent checkouts cannot both create a first-timer purchase.
    user_model = get_user_model()
    with transaction.atomic():
        user = user_model.objects.select_for_update().get(pk=user.pk)
        return _checkout_plans(
            user=user,
            items=items,
            promo_code=promo_code,
            payment_method=payment_method,
            gift_recipient=gift_recipient,
        )


def _checkout_plans(
    *,
    user,
    items: list[dict],
    promo_code: str | None = None,
    payment_method: str | None = None,
    gift_recipient: dict | None = None,
) -> dict:
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

    first_timer_items = [item for item in resolved_items if item["plan"].is_first_timer]
    if first_timer_items:
        if (
            len(first_timer_items) != 1
            or len(resolved_items) != 1
            or first_timer_items[0]["quantity"] != 1
        ):
            raise ValueError("El pack de primera vez debe comprarse solo y en una cantidad de 1.")
        if gift_recipient:
            raise ValueError("El pack de primera vez no puede enviarse como regalo.")
        if PlanPurchase.objects.filter(user=user).exists():
            raise ValueError(
                "El pack de primera vez está disponible solo para usuarios sin compras previas."
            )

    promo = None
    has_gift_product = any(
        item["plan"].type in {constants.PLAN_TYPE_GIFT_CARD, constants.PLAN_TYPE_GIFT_PACK}
        for item in resolved_items
    )
    if has_gift_product and not gift_recipient:
        raise ValueError("Indica los datos de la persona que recibirá el regalo.")

    discount = Decimal("0.00")
    if promo_code:
        promo = get_valid_promo_code(promo_code)
        discount = compute_discount_amount(subtotal=subtotal, promo=promo)

    remaining_discount = discount
    purchases = []
    gift_cards = []
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
        if not settings.ENABLE_PSP_PAYMENTS and not gift_recipient:
            WalletService.activate_purchase(purchase)
        purchases.append(_serialize_purchase(purchase))

        if gift_recipient:
            expires_at = timezone.now() + timedelta(
                days=getattr(settings, "GIFT_CARD_EXPIRY_DAYS", 365)
            )
            for _ in range(item["quantity"]):
                gift_card = GiftCard.objects.create(
                    plan=item["plan"],
                    purchase=purchase,
                    issuer=user,
                    recipient_name=gift_recipient.get("name", "").strip(),
                    recipient_email=gift_recipient["email"].strip().lower(),
                    message=gift_recipient.get("message", "").strip(),
                    send_at=gift_recipient.get("send_at"),
                    expires_at=expires_at,
                )
                gift_cards.append(gift_card)
                if not gift_card.send_at or gift_card.send_at <= timezone.now():
                    send_gift_recipient_email(gift_card)
            send_gift_purchase_receipt_email(purchase, item["quantity"])

    return {
        "purchases": purchases,
        "subtotal": float(subtotal),
        "discount": float(discount),
        "total": float(_quantize(subtotal - discount)),
        "promo_code": promo.code if promo else None,
        "payment_method": method or None,
        "first_timer_onboarding": bool(first_timer_items),
        "gifts": [
            {
                "id": gift_card.id,
                "code": gift_card.code,
                "plan_name": gift_card.plan.name,
                "recipient_email": gift_card.recipient_email,
                "expires_at": gift_card.expires_at,
                "send_at": gift_card.send_at,
            }
            for gift_card in gift_cards
        ],
    }
