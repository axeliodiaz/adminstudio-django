from django.urls import path

from apps.members.views import (
    AdminMemberDetailView,
    AdminMemberListView,
    MemberView,
    ReservationView,
)

urlpatterns = [
    path("admin/", AdminMemberListView.as_view(), name="admin-members"),
    path(
        "admin/<uuid:member_id>/",
        AdminMemberDetailView.as_view(),
        name="admin-member-detail",
    ),
    path("register/", MemberView.as_view({"post": "create"}), name="member-register"),
    path(
        "get_member/",
        MemberView.as_view({"get": "get_member"}),
        name="member-get",
    ),
    path(
        "reservations/",
        ReservationView.as_view({"post": "create", "get": "list"}),
        name="reservations",
    ),
    path(
        "reservations/cancel/",
        ReservationView.as_view({"post": "cancel"}),
        name="reservation-cancel",
    ),
    path(
        "reservations/<uuid:schedule_id>/change-spot/",
        ReservationView.as_view({"patch": "change_spot"}),
        name="reservation-change-spot",
    ),
]
