from django.urls import path

from apps.users.views import (
    LoginView,
    ClerkSessionView,
    CurrentUserView,
    AdminUserListView,
    AdminUserDetailView,
    AdminUserPasswordRecoveryView,
    AdminUserEmailChangeView,
    EmailChangeConfirmView,
    ChangePasswordView,
    PasswordRecoveryRequestView,
    PasswordRecoveryConfirmView,
)

app_name = "users"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("clerk/", ClerkSessionView.as_view(), name="clerk"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("users/", AdminUserListView.as_view(), name="users"),
    path(
        "users/<uuid:user_id>/password-recovery/",
        AdminUserPasswordRecoveryView.as_view(),
        name="user-password-recovery",
    ),
    path(
        "users/<uuid:user_id>/email-change/",
        AdminUserEmailChangeView.as_view(),
        name="user-email-change",
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
    path(
        "email-change/confirm/<uuid:change_uuid>/",
        EmailChangeConfirmView.as_view(),
        name="email-change-confirm",
    ),
]
