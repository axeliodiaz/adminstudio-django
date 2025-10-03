from django.urls import path

from apps.members.views import MemberView

urlpatterns = [
    path("register/", MemberView.as_view({"post": "create"}), name="member-register"),
]
