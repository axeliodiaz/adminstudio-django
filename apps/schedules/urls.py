from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.schedules.views import (
    AdminScheduleDetailView,
    AdminScheduleListView,
    ScheduleViewSet,
)

router = DefaultRouter()
router.register(r"", ScheduleViewSet, basename="schedule")

urlpatterns = [
    path("admin/schedules/", AdminScheduleListView.as_view(), name="admin-schedule-list"),
    path(
        "admin/schedules/<uuid:schedule_id>/",
        AdminScheduleDetailView.as_view(),
        name="admin-schedule-detail",
    ),
    path("", include(router.urls)),
]
