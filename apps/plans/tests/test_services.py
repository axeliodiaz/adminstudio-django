"""Tests for apps.plans.services."""

import uuid

import pytest

from apps.plans.models import Plan
from apps.plans.schemas import PlanSchema
from apps.plans.services import get_plan_by_id, get_plans
from apps.plans import constants


class TestGetPlanById:
    @pytest.mark.django_db
    def test_returns_plan_schema_when_exists(self):
        # Arrange
        plan = Plan.objects.create(
            name="Gold",
            type=constants.PLAN_TYPE_MEMBERSHIP,
            price=49.99,
            duration_days=30,
            classes_included=None,
            is_active=True,
            is_popular=True,
            is_highlighted=False,
        )
        # Act
        result = get_plan_by_id(plan.id)
        # Assert
        assert isinstance(result, PlanSchema)
        assert result.id == plan.id
        assert result.name == plan.name
        assert result.type == plan.type
        assert result.price == plan.price
        assert result.is_active is True

    @pytest.mark.django_db
    def test_raises_does_not_exist_for_unknown_id(self):
        with pytest.raises(Plan.DoesNotExist):
            get_plan_by_id(uuid.uuid4())


class TestGetPlans:
    @pytest.mark.django_db
    def test_returns_only_active_plans_as_schemas(self):
        # Arrange: one active and one inactive plan
        active = Plan.objects.create(
            name="Active Plan",
            type=constants.PLAN_TYPE_MEMBERSHIP,
            price=29.99,
            duration_days=30,
            classes_included=None,
            is_active=True,
            is_popular=False,
            is_highlighted=False,
        )
        Plan.objects.create(
            name="Inactive Plan",
            type=constants.PLAN_TYPE_PACKAGE,
            price=99.0,
            duration_days=None,
            classes_included=10,
            is_active=False,
            is_popular=False,
            is_highlighted=False,
        )
        # Act
        result = get_plans()
        # Assert type and filtering
        assert isinstance(result, list)
        assert all(isinstance(item, PlanSchema) for item in result)
        assert {str(p.id) for p in result} == {str(active.id)}
        # Validate a few fields on the active plan
        only = result[0]
        assert only.name == active.name
        assert only.type == active.type
        assert only.price == active.price
