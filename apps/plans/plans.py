from typing import List
from uuid import UUID

from apps.plans.models import Plan


def get_plans() -> List[Plan]:
    """
    Return all active plans.
    """
    return list(
        Plan.objects.filter(is_active=True)
        .prefetch_related("benefits")
        .order_by("-is_highlighted", "-is_popular", "-created")
    )


def get_plan_by_id(plan_id: UUID | str) -> Plan:
    """Return a single Plan by id or raise Plan.DoesNotExist."""
    return Plan.objects.prefetch_related("benefits").get(id=plan_id)
