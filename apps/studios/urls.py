from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.studios.views import (
    AddressViewSet,
    AdminRoomDetailView,
    AdminRoomListView,
    AdminStudioDetailView,
    AdminStudioListView,
    RoomViewSet,
    StudioViewSet,
)

router = DefaultRouter()
router.register(r"studios", StudioViewSet, basename="studio")
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"addresses", AddressViewSet, basename="address")

urlpatterns = [
    path("admin/studios/", AdminStudioListView.as_view(), name="admin-studio-list"),
    path(
        "admin/studios/<uuid:studio_id>/",
        AdminStudioDetailView.as_view(),
        name="admin-studio-detail",
    ),
    path("admin/rooms/", AdminRoomListView.as_view(), name="admin-room-list"),
    path(
        "admin/rooms/<uuid:room_id>/",
        AdminRoomDetailView.as_view(),
        name="admin-room-detail",
    ),
    path("", include(router.urls)),
]
