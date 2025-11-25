from django.urls import path

from apps.members.views import MemberView, ReservationView

urlpatterns = [
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
