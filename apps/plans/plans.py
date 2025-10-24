from typing import List
from uuid import UUID

from apps.plans.models import Plan


def get_plans() -> List[Plan]:
    """
    Return all active plans.
    """
    return list(Plan.objects.filter(is_active=True))


def get_plan_by_id(plan_id: UUID | str) -> Plan:
    """Return a single Plan by id or raise Plan.DoesNotExist."""
    return Plan.objects.get(id=plan_id)
