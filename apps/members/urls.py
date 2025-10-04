from django.urls import path

from apps.members.views import MemberView, ReservationView

urlpatterns = [
    path("register/", MemberView.as_view({"post": "create"}), name="member-register"),
    path("reservations/", ReservationView.as_view({"post": "create"}), name="reservation-create"),
]
