from django.urls import path

from apps.users.views import LoginView, ChangePasswordView

app_name = "users"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
