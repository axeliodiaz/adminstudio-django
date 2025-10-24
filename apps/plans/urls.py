from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.plans.views import PlanViewSet

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")

urlpatterns = [
    path("", include(router.urls)),
]
