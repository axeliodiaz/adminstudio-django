import pytest

from apps.plans.models import Benefit, Plan


class TestPlanModelBenefitsList:
    @pytest.mark.django_db
    def test_returns_only_active_benefits_sorted_by_name(self):
        # Arrange
        plan = Plan.objects.create(name="Pro", type="MEMBERSHIP", price=30.0, is_active=True)
        b1 = Benefit.objects.create(name="Zeta", description="Z", is_active=True)
        b2 = Benefit.objects.create(name="Alpha", description="A", is_active=True)
        b3 = Benefit.objects.create(name="Mid", description="M", is_active=False)
        plan.benefits.set([b1, b2, b3])

        # Act
        result = plan.benefits_list

        # Assert
        assert [b.name for b in result] == [
            "Alpha",
            "Zeta",
        ], "Should include only active and be name-ordered"
        assert all(b.is_active for b in result), "All returned benefits must be active"

    @pytest.mark.django_db
    def test_empty_when_no_benefits(self):
        plan = Plan.objects.create(name="Basic", type="PACKAGE", price=10.0, is_active=True)
        assert plan.benefits_list == []

    @pytest.mark.django_db
    def test_empty_when_all_inactive(self):
        plan = Plan.objects.create(name="Starter", type="PACKAGE", price=15.0, is_active=True)
        b1 = Benefit.objects.create(name="A", description="a", is_active=False)
        b2 = Benefit.objects.create(name="B", description="b", is_active=False)
        plan.benefits.set([b1, b2])
        assert plan.benefits_list == []
