from django.urls import path

from apps.analytics.services import ADMIN_DASHBOARD_MODULES
from apps.analytics.views import (
    AdminDashboardModuleView,
    AdminDashboardView,
    AdminMemberStatsView,
    MemberStatsView,
)

urlpatterns = [
    path("me/", MemberStatsView.as_view(), name="member-stats"),
    path(
        "admin/users/<uuid:user_id>/",
        AdminMemberStatsView.as_view(),
        name="admin-member-stats",
    ),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    *[
        path(
            f"admin/dashboard/modules/{module}/",
            AdminDashboardModuleView.as_view(module=module),
            name=f"admin-dashboard-{module}",
        )
        for module in ADMIN_DASHBOARD_MODULES
    ],
]
