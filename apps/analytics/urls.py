from django.urls import path

from apps.analytics.views import AdminDashboardView, MemberStatsView

urlpatterns = [
    path("me/", MemberStatsView.as_view(), name="member-stats"),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
]
