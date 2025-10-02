from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.instructors.views import InstructorViewSet

router = DefaultRouter()
router.register(r"instructors", InstructorViewSet, basename="instructor")

urlpatterns = [
    path("", include(router.urls)),
]
