from django.urls import path

from apps.users.views import (
    LoginView,
    CurrentUserView,
    AdminUserListView,
    AdminUserDetailView,
    AdminUserPasswordRecoveryView,
    ChangePasswordView,
    PasswordRecoveryRequestView,
    PasswordRecoveryConfirmView,
)

app_name = "users"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("users/", AdminUserListView.as_view(), name="users"),
    path(
        "users/<uuid:user_id>/password-recovery/",
        AdminUserPasswordRecoveryView.as_view(),
        name="user-password-recovery",
    ),
    path("users/<uuid:user_id>/", AdminUserDetailView.as_view(), name="user-detail"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path(
        "password-recovery/",
        PasswordRecoveryRequestView.as_view(),
        name="password-recovery-request",
    ),
    path(
        "password-recovery/confirm/",
        PasswordRecoveryConfirmView.as_view(),
        name="password-recovery-confirm",
    ),
]
