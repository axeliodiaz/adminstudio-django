"""Services for plans app.

Expose functions that return schemas for consumption by views or other layers.
"""

from uuid import UUID

from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.plans import constants
from apps.plans.models import Benefit, Plan
from apps.plans.plans import get_plan_by_id as get_plan_model_by_id, get_plans as get_plan_models
from apps.plans.schemas import (
    AdminBenefitSchema,
    AdminPlanSchema,
    BenefitSchema,
    PlanSchema,
)


def get_plans() -> list[PlanSchema]:
    """Return a list of PlanSchema for all active plans."""
    return [PlanSchema.model_validate(obj) for obj in get_plan_models()]


def get_plan_by_id(plan_id: UUID | str) -> PlanSchema:
    """Return a single PlanSchema by id or raise Plan.DoesNotExist."""
    return PlanSchema.model_validate(get_plan_model_by_id(plan_id))


def _serialize_admin_plan(plan: Plan) -> dict:
    benefits = list(plan.benefits.filter(is_removed=False).order_by("name"))
    payload = {
        "id": plan.id,
        "created": plan.created,
        "modified": plan.modified,
        "name": plan.name,
        "type": plan.type,
        "price": plan.price,
        "duration_days": plan.duration_days,
        "classes_included": plan.classes_included,
        "guest_passes_included": plan.guest_passes_included,
        "is_active": plan.is_active,
        "is_popular": plan.is_popular,
        "is_highlighted": plan.is_highlighted,
        "is_first_timer": plan.is_first_timer,
        "benefits": [BenefitSchema.model_validate(benefit) for benefit in benefits],
        "benefit_ids": [benefit.id for benefit in benefits],
    }
    return AdminPlanSchema.model_validate(payload).model_dump(mode="json")


def list_admin_plans(
    *,
    search: str | None = None,
    plan_type: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Return non-deleted plans for the staff admin list (active and inactive)."""
    queryset = Plan.objects.prefetch_related("benefits").order_by(
        "-is_highlighted",
        "-is_popular",
        "name",
    )

    if plan_type in {
        constants.PLAN_TYPE_MEMBERSHIP,
        constants.PLAN_TYPE_PACKAGE,
        constants.PLAN_TYPE_GIFT_CARD,
        constants.PLAN_TYPE_GIFT_PACK,
    }:
        queryset = queryset.filter(type=plan_type)

    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(name__icontains=term) | Q(benefits__name__icontains=term)
        ).distinct()

    return [_serialize_admin_plan(plan) for plan in queryset]


def get_admin_plan(*, plan_id: str | UUID) -> dict:
    """Return one non-deleted plan for the staff admin."""
    plan = get_object_or_404(Plan.objects.prefetch_related("benefits"), id=plan_id)
    return _serialize_admin_plan(plan)


def _validate_plan_write(*, data: dict, require_required_fields: bool) -> None:
    if require_required_fields:
        if not (data.get("name") or "").strip():
            raise ValueError("El nombre del plan es obligatorio.")
        if data.get("type") not in {
            constants.PLAN_TYPE_MEMBERSHIP,
            constants.PLAN_TYPE_PACKAGE,
            constants.PLAN_TYPE_GIFT_CARD,
            constants.PLAN_TYPE_GIFT_PACK,
        }:
            raise ValueError("El tipo de plan es inválido.")
        if data.get("price") is None:
            raise ValueError("El precio es obligatorio.")

    if "name" in data and data["name"] is not None and not str(data["name"]).strip():
        raise ValueError("El nombre del plan es obligatorio.")

    if (
        "type" in data
        and data["type"] is not None
        and data["type"]
        not in {
            constants.PLAN_TYPE_MEMBERSHIP,
            constants.PLAN_TYPE_PACKAGE,
            constants.PLAN_TYPE_GIFT_CARD,
            constants.PLAN_TYPE_GIFT_PACK,
        }
    ):
        raise ValueError("El tipo de plan es inválido.")

    if "price" in data and data["price"] is not None and float(data["price"]) < 0:
        raise ValueError("El precio no puede ser negativo.")

    for field in ("duration_days", "classes_included", "guest_passes_included"):
        if field in data and data[field] is not None and int(data[field]) < 0:
            raise ValueError(f"{field} no puede ser negativo.")


def _resolve_benefits(benefit_ids: list[UUID] | None) -> list[Benefit]:
    if benefit_ids is None:
        return []
    if not benefit_ids:
        return []

    benefits = list(Benefit.objects.filter(id__in=benefit_ids, is_removed=False))
    found_ids = {benefit.id for benefit in benefits}
    missing = [str(benefit_id) for benefit_id in benefit_ids if benefit_id not in found_ids]
    if missing:
        raise ValueError(f"Beneficios no encontrados: {', '.join(missing)}")
    return benefits


def create_admin_plan(*, data: dict) -> dict:
    """Create a plan from the staff admin."""
    _validate_plan_write(data=data, require_required_fields=True)

    benefit_ids = data.get("benefit_ids")
    benefits = _resolve_benefits(benefit_ids)

    plan = Plan.objects.create(
        name=str(data["name"]).strip(),
        type=data["type"],
        price=float(data["price"]),
        duration_days=data.get("duration_days"),
        classes_included=data.get("classes_included"),
        guest_passes_included=data.get("guest_passes_included"),
        is_active=bool(data.get("is_active", False)),
        is_popular=bool(data.get("is_popular", False)),
        is_highlighted=bool(data.get("is_highlighted", False)),
        is_first_timer=bool(data.get("is_first_timer", False)),
    )
    if benefit_ids is not None:
        plan.benefits.set(benefits)

    return _serialize_admin_plan(plan)


def update_admin_plan(*, plan_id: str | UUID, data: dict) -> dict:
    """Update staff-editable plan fields."""
    plan = get_object_or_404(Plan.objects.prefetch_related("benefits"), id=plan_id)
    _validate_plan_write(data=data, require_required_fields=False)

    scalar_fields = {
        "name",
        "type",
        "price",
        "duration_days",
        "classes_included",
        "guest_passes_included",
        "is_active",
        "is_popular",
        "is_highlighted",
        "is_first_timer",
    }
    dirty_fields: list[str] = []

    for field, value in data.items():
        if field not in scalar_fields:
            continue
        if field == "name" and value is not None:
            value = str(value).strip()
        if field == "price" and value is not None:
            value = float(value)
        setattr(plan, field, value)
        dirty_fields.append(field)

    if dirty_fields:
        plan.save(update_fields=list(dict.fromkeys(dirty_fields)))

    if "benefit_ids" in data:
        benefits = _resolve_benefits(data.get("benefit_ids"))
        plan.benefits.set(benefits)

    plan.refresh_from_db()
    return _serialize_admin_plan(plan)


def list_admin_benefits(*, search: str | None = None, only_active: bool = False) -> list[dict]:
    """Return benefits for the staff admin plan editor."""
    queryset = Benefit.objects.filter(is_removed=False).order_by("name")
    if only_active:
        queryset = queryset.filter(is_active=True)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(Q(name__icontains=term) | Q(description__icontains=term))

    return [
        AdminBenefitSchema.model_validate(benefit).model_dump(mode="json") for benefit in queryset
    ]
