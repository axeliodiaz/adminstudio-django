from django.urls import path

from apps.users.views import LoginView, CurrentUserView, ChangePasswordView

app_name = "users"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
