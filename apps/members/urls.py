from django.urls import path

from apps.members.views import (
    AdminAttendanceDayView,
    AdminAttendanceMarkMissedView,
    AdminAttendanceRosterView,
    AdminMemberDetailView,
    AdminMemberListView,
    AdminReservationAttendanceView,
    AdminReservationCancelView,
    AdminReservationChangeSpotView,
    AdminReservationDetailView,
    AdminReservationListView,
    MemberView,
    ReservationView,
    WaitlistView,
)

urlpatterns = [
    path(
        "admin/reservations/",
        AdminReservationListView.as_view(),
        name="admin-reservation-list",
    ),
    path(
        "admin/reservations/<uuid:reservation_id>/",
        AdminReservationDetailView.as_view(),
        name="admin-reservation-detail",
    ),
    path(
        "admin/reservations/<uuid:reservation_id>/cancel/",
        AdminReservationCancelView.as_view(),
        name="admin-reservation-cancel",
    ),
    path(
        "admin/reservations/<uuid:reservation_id>/change-spot/",
        AdminReservationChangeSpotView.as_view(),
        name="admin-reservation-change-spot",
    ),
    path(
        "admin/reservations/<uuid:reservation_id>/attendance/",
        AdminReservationAttendanceView.as_view(),
        name="admin-reservation-attendance",
    ),
    path(
        "admin/attendance/",
        AdminAttendanceDayView.as_view(),
        name="admin-attendance-day",
    ),
    path(
        "admin/attendance/<uuid:schedule_id>/",
        AdminAttendanceRosterView.as_view(),
        name="admin-attendance-roster",
    ),
    path(
        "admin/attendance/<uuid:schedule_id>/mark-missed/",
        AdminAttendanceMarkMissedView.as_view(),
        name="admin-attendance-mark-missed",
    ),
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
    path(
        "reservations/<uuid:reservation_id>/",
        ReservationView.as_view({"delete": "destroy"}),
        name="reservation-detail",
    ),
    path(
        "waitlist/",
        WaitlistView.as_view({"get": "list", "post": "create"}),
        name="waitlist",
    ),
    path(
        "waitlist/<uuid:waitlist_id>/",
        WaitlistView.as_view({"delete": "destroy"}),
        name="waitlist-detail",
    ),
    path(
        "waitlist/<uuid:waitlist_id>/confirm/",
        WaitlistView.as_view({"post": "confirm"}),
        name="waitlist-confirm",
    ),
]
