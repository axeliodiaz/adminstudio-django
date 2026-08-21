import pytest
from model_bakery import baker

from apps.plans.models import Plan


@pytest.fixture
@pytest.mark.django_db
def plan() -> Plan:
    return baker.make(Plan)


@pytest.fixture
@pytest.mark.django_db
def plans_three() -> list[Plan]:
    return baker.make(Plan, _quantity=3)
