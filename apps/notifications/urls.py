from django.urls import path

from .email_smoke import email_smoke
from .views import FlushPendingNotificationsView

urlpatterns = [
    path("email-smoke/", email_smoke),
    path(
        "flush-pending/",
        FlushPendingNotificationsView.as_view(),
        name="notifications-flush-pending",
    ),
]
