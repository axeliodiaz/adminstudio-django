from django.urls import path

from apps.members.views import MemberRegistrationView

urlpatterns = [
    path("register/", MemberRegistrationView.as_view(), name="member-register"),
]
