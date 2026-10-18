"""Admin API for the precomputed reports (CYC-440). Superusers only."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports import services
from apps.reports.builders import REPORT_BUILDERS, REPORT_CATALOG, parse_range
from apps.reports.models import ClassMetrics, DailyMetrics
from apps.reports.permissions import IsReportsAdmin


class ReportsCatalogView(APIView):
    """GET /api/reports/ — available reports and data freshness."""

    permission_classes = [IsAuthenticated, IsReportsAdmin]

    def get(self, request, *args, **kwargs):
        last_computed = (
            DailyMetrics.objects.order_by("-computed_at")
            .values_list("computed_at", flat=True)
            .first()
        )
        first_day = DailyMetrics.objects.order_by("date").values_list("date", flat=True).first()
        return Response(
            {
                "module": "reports",
                "reports": REPORT_CATALOG,
                "freshness": {
                    "first_day": first_day.isoformat() if first_day else None,
                    "last_computed_at": last_computed,
                    "model": "event-driven + manual refresh (no cron on the free tier)",
                },
                "counts": {
                    "days": DailyMetrics.objects.count(),
                    "classes": ClassMetrics.objects.count(),
                },
            }
        )


class ReportDetailView(APIView):
    """GET /api/reports/<key>/?from=YYYY-MM-DD&to=YYYY-MM-DD."""

    permission_classes = [IsAuthenticated, IsReportsAdmin]

    def get(self, request, report_key, *args, **kwargs):
        builder = REPORT_BUILDERS.get(report_key)
        if builder is None:
            return Response({"detail": "Reporte desconocido."}, status=404)
        from_day, to_day = parse_range(request.query_params)
        payload = builder(from_day, to_day)
        payload["report"] = report_key
        payload["from"] = from_day.isoformat()
        payload["to"] = to_day.isoformat()
        return Response(payload)


class ReportsRefreshView(APIView):
    """POST /api/reports/refresh/ — full rebuild of the precomputed tables."""

    permission_classes = [IsAuthenticated, IsReportsAdmin]

    def post(self, request, *args, **kwargs):
        summary = services.refresh_all()
        return Response({"detail": "Reportes recalculados.", **summary})
