from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.plans.views import (
    AdminBenefitListView,
    AdminPlanDetailView,
    AdminPlanListView,
    AdminPromoCodeDetailView,
    AdminPromoCodeListView,
    CheckoutView,
    PlanViewSet,
    RedeemGiftCardView,
    ValidatePromoCodeView,
)

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")

urlpatterns = [
    path(
        "purchase/",
        PlanViewSet.as_view({"post": "purchase"}),
        name="plan-purchase",
    ),
    path("checkout/", CheckoutView.as_view(), name="plan-checkout"),
    path("gifts/redeem/", RedeemGiftCardView.as_view(), name="gift-card-redeem"),
    path("validate-promo/", ValidatePromoCodeView.as_view(), name="plan-validate-promo"),
    path("admin/promo-codes/", AdminPromoCodeListView.as_view(), name="admin-promo-list"),
    path(
        "admin/promo-codes/<uuid:promo_id>/",
        AdminPromoCodeDetailView.as_view(),
        name="admin-promo-detail",
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
