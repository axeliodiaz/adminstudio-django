"""Services for plans app.

Expose functions that return schemas for consumption by views or other layers.
"""

from uuid import UUID

from apps.plans.plans import get_plan_by_id as get_plan_model_by_id, get_plans as get_plan_models
from apps.plans.schemas import PlanSchema


def get_plans() -> list[PlanSchema]:
    """Return a list of PlanSchema for all active plans."""
    return [PlanSchema.model_validate(obj) for obj in get_plan_models()]


def get_plan_by_id(plan_id: UUID | str) -> PlanSchema:
    """Return a single PlanSchema by id or raise Plan.DoesNotExist."""
    return PlanSchema.model_validate(get_plan_model_by_id(plan_id))
