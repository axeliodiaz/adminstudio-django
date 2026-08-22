"""Validation and staff CRUD for promotional codes."""

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.plans import constants
from apps.plans.models import Plan, PromoCode
from apps.plans.schemas import AdminPromoCodeSchema, PromoCodeSchema

TWOPLACES = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def normalize_code(code: str | None) -> str:
    return (code or "").strip().upper()


def is_promo_currently_valid(promo: PromoCode, *, at=None) -> bool:
    now = at or timezone.now()
    if not promo.is_active:
        return False
    if promo.valid_from and now < promo.valid_from:
        return False
    if promo.valid_until and now > promo.valid_until:
        return False
    return True


def get_valid_promo_code(code: str) -> PromoCode:
    normalized = normalize_code(code)
    if not normalized:
        raise ValueError("Ingresa un código promocional.")

    promo = PromoCode.objects.filter(code=normalized, is_removed=False).first()
    if promo is None:
        raise ValueError("El código promocional no existe.")
    if not promo.is_active:
        raise ValueError("El código promocional no está activo.")
    if not is_promo_currently_valid(promo):
        raise ValueError("El código promocional está fuera de su rango de fechas.")
    return promo


def compute_discount_amount(*, subtotal: Decimal, promo: PromoCode) -> Decimal:
    if subtotal <= 0:
        return Decimal("0.00")

    if promo.discount_type == constants.DISCOUNT_TYPE_PERCENT:
        amount = subtotal * (Decimal(str(promo.discount_value)) / Decimal("100"))
    else:
        amount = Decimal(str(promo.discount_value))

    if amount < 0:
        amount = Decimal("0.00")
    if amount > subtotal:
        amount = subtotal
    return _quantize(amount)


def serialize_promo(promo: PromoCode, *, subtotal: Decimal | None = None) -> dict:
    discount_amount = None
    total = None
    if subtotal is not None:
        discount_amount = compute_discount_amount(subtotal=subtotal, promo=promo)
        total = _quantize(subtotal - discount_amount)

    payload = {
        "id": promo.id,
        "code": promo.code,
        "description": promo.description or "",
        "is_active": promo.is_active,
        "valid_from": promo.valid_from,
        "valid_until": promo.valid_until,
        "discount_type": promo.discount_type,
        "discount_value": float(promo.discount_value),
        "discount_amount": float(discount_amount) if discount_amount is not None else None,
        "subtotal": float(subtotal) if subtotal is not None else None,
        "total": float(total) if total is not None else None,
    }
    return PromoCodeSchema.model_validate(payload).model_dump(mode="json")


def validate_promo_for_checkout(
    *,
    code: str,
    plan: Plan | None = None,
    subtotal: Decimal | None = None,
) -> tuple[PromoCode, dict]:
    promo = get_valid_promo_code(code)
    resolved_subtotal = subtotal
    if resolved_subtotal is None and plan is not None:
        resolved_subtotal = _quantize(Decimal(str(plan.price)))
    return promo, serialize_promo(promo, subtotal=resolved_subtotal)


def _serialize_admin_promo(promo: PromoCode) -> dict:
    return AdminPromoCodeSchema.model_validate(promo).model_dump(mode="json")


def list_admin_promo_codes(
    *,
    search: str | None = None,
    status: str | None = None,
) -> list[dict]:
    queryset = PromoCode.objects.filter(is_removed=False).order_by("-created")

    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(Q(code__icontains=term) | Q(description__icontains=term))

    return [_serialize_admin_promo(promo) for promo in queryset]


def get_admin_promo_code(*, promo_id: str | UUID) -> dict:
    promo = get_object_or_404(PromoCode.objects.filter(is_removed=False), id=promo_id)
    return _serialize_admin_promo(promo)


def _validate_promo_write(*, data: dict, require_required_fields: bool) -> None:
    if require_required_fields:
        if not normalize_code(data.get("code")):
            raise ValueError("El código es obligatorio.")
        if data.get("valid_from") is None or data.get("valid_until") is None:
            raise ValueError("El rango de fechas es obligatorio.")
        if data.get("discount_type") not in {
            constants.DISCOUNT_TYPE_PERCENT,
            constants.DISCOUNT_TYPE_FIXED,
        }:
            raise ValueError("El tipo de descuento es inválido.")
        if data.get("discount_value") is None:
            raise ValueError("El valor del descuento es obligatorio.")

    if "code" in data and data["code"] is not None and not normalize_code(data["code"]):
        raise ValueError("El código es obligatorio.")

    if (
        "discount_type" in data
        and data["discount_type"] is not None
        and data["discount_type"]
        not in {
            constants.DISCOUNT_TYPE_PERCENT,
            constants.DISCOUNT_TYPE_FIXED,
        }
    ):
        raise ValueError("El tipo de descuento es inválido.")

    if "discount_value" in data and data["discount_value"] is not None:
        value = Decimal(str(data["discount_value"]))
        if value < 0:
            raise ValueError("El valor del descuento no puede ser negativo.")
        discount_type = data.get("discount_type")
        if discount_type == constants.DISCOUNT_TYPE_PERCENT and value > 100:
            raise ValueError("El porcentaje de descuento no puede ser mayor a 100.")

    valid_from = data.get("valid_from")
    valid_until = data.get("valid_until")
    if valid_from is not None and valid_until is not None and valid_until < valid_from:
        raise ValueError("La fecha de término debe ser posterior al inicio.")


def create_admin_promo_code(*, data: dict) -> dict:
    _validate_promo_write(data=data, require_required_fields=True)
    code = normalize_code(data["code"])
    if PromoCode.objects.filter(code=code, is_removed=False).exists():
        raise ValueError("Ya existe un código promocional con ese valor.")

    promo = PromoCode.objects.create(
        code=code,
        description=(data.get("description") or "").strip(),
        is_active=bool(data.get("is_active", False)),
        valid_from=data["valid_from"],
        valid_until=data["valid_until"],
        discount_type=data["discount_type"],
        discount_value=Decimal(str(data["discount_value"])),
    )
    return _serialize_admin_promo(promo)


def update_admin_promo_code(*, promo_id: str | UUID, data: dict) -> dict:
    promo = get_object_or_404(PromoCode.objects.filter(is_removed=False), id=promo_id)
    merged = {
        "code": data.get("code", promo.code),
        "valid_from": data.get("valid_from", promo.valid_from),
        "valid_until": data.get("valid_until", promo.valid_until),
        "discount_type": data.get("discount_type", promo.discount_type),
        "discount_value": data.get("discount_value", promo.discount_value),
        "description": data.get("description", promo.description),
        "is_active": data.get("is_active", promo.is_active),
    }
    _validate_promo_write(data=merged, require_required_fields=True)

    if "code" in data and data["code"] is not None:
        code = normalize_code(data["code"])
        if PromoCode.objects.filter(code=code, is_removed=False).exclude(id=promo.id).exists():
            raise ValueError("Ya existe un código promocional con ese valor.")
        promo.code = code

    scalar_fields = {
        "description",
        "is_active",
        "valid_from",
        "valid_until",
        "discount_type",
        "discount_value",
    }
    dirty_fields = ["code"] if "code" in data and data["code"] is not None else []

    for field, value in data.items():
        if field not in scalar_fields:
            continue
        if field == "description" and value is not None:
            value = str(value).strip()
        if field == "discount_value" and value is not None:
            value = Decimal(str(value))
        setattr(promo, field, value)
        dirty_fields.append(field)

    if dirty_fields:
        promo.save(update_fields=list(dict.fromkeys(dirty_fields)))

    promo.refresh_from_db()
    return _serialize_admin_promo(promo)
