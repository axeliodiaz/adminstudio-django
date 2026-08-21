import uuid

import pytest

from apps.plans.models import Plan
from apps.plans.plans import get_plan_by_id


class TestGetPlanById:
    @pytest.mark.django_db
    def test_returns_plan_when_exists(self, plan):
        fetched = get_plan_by_id(plan.id)
        assert isinstance(fetched, Plan)
        assert fetched.id == plan.id

    @pytest.mark.django_db
    def test_raises_does_not_exist_for_unknown_id(self):
        with pytest.raises(Plan.DoesNotExist):
            get_plan_by_id(uuid.uuid4())
