from django.urls import path

from apps.reports.views import ReportDetailView, ReportsCatalogView, ReportsRefreshView

urlpatterns = [
    path("", ReportsCatalogView.as_view(), name="reports-catalog"),
    path("refresh/", ReportsRefreshView.as_view(), name="reports-refresh"),
    path("<str:report_key>/", ReportDetailView.as_view(), name="reports-detail"),
]
