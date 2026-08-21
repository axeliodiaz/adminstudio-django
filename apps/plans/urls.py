from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.plans.views import (
    AdminBenefitListView,
    AdminPlanDetailView,
    AdminPlanListView,
    PlanViewSet,
)

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")

urlpatterns = [
    path(
        "purchase/",
        PlanViewSet.as_view({"post": "purchase"}),
        name="plan-purchase",
    ),
    path("admin/plans/", AdminPlanListView.as_view(), name="admin-plan-list"),
    path(
        "admin/plans/<uuid:plan_id>/",
        AdminPlanDetailView.as_view(),
        name="admin-plan-detail",
    ),
    path(
        "admin/benefits/",
        AdminBenefitListView.as_view(),
        name="admin-benefit-list",
    ),
    path("", include(router.urls)),
]
