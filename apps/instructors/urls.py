from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.instructors.views import (
    AdminInstructorDetailView,
    AdminInstructorListView,
    InstructorViewSet,
)

router = DefaultRouter()
router.register(r"instructors", InstructorViewSet, basename="instructor")

urlpatterns = [
    path("admin/", AdminInstructorListView.as_view(), name="admin-instructors"),
    path(
        "admin/<uuid:instructor_id>/",
        AdminInstructorDetailView.as_view(),
        name="admin-instructor-detail",
    ),
    path("", include(router.urls)),
]
