from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.schedules.views import ScheduleViewSet

router = DefaultRouter()
router.register(r"schedules", ScheduleViewSet, basename="schedule")

urlpatterns = [
    path("", include(router.urls)),
]
