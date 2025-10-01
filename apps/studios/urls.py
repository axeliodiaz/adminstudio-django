from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.studios.views import RoomViewSet, StudioViewSet

router = DefaultRouter()
router.register(r"studios", StudioViewSet, basename="studio")
router.register(r"rooms", RoomViewSet, basename="room")

urlpatterns = [
    path("", include(router.urls)),
]
