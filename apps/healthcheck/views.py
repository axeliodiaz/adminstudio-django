from django.db import connections
from django.db.utils import OperationalError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class HealthcheckView(APIView):
    """
    Healthcheck endpoint implemented as a DRF class-based view.

    GET returns JSON with overall status and checks for:
      - application (always ok if code runs)
      - database (obtain a cursor)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        checks = {"app": "ok"}

        db_ok = True
        try:
            connections["default"].cursor()
            checks["database"] = "ok"
        except OperationalError as exc:
            db_ok = False
            checks["database"] = f"error: {exc.__class__.__name__}"

        overall_ok = db_ok
        http_status = (
            status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(
            {"status": "ok" if overall_ok else "error", "checks": checks},
            status=http_status,
        )
