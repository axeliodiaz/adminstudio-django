from django.urls import path

from apps.analytics.views import AdminDashboardView, AdminMemberStatsView, MemberStatsView

urlpatterns = [
    path("me/", MemberStatsView.as_view(), name="member-stats"),
    path(
        "admin/users/<uuid:user_id>/",
        AdminMemberStatsView.as_view(),
        name="admin-member-stats",
    ),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
]
