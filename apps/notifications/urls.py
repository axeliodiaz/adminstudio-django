from django.urls import path

from .views import FlushPendingNotificationsView

urlpatterns = [
    path(
        "flush-pending/",
        FlushPendingNotificationsView.as_view(),
        name="notifications-flush-pending",
    ),
]
