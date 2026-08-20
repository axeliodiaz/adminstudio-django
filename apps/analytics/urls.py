from django.urls import path

from apps.analytics.views import AdminDashboardView

urlpatterns = [
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
]
