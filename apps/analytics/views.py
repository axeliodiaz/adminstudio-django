from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import get_admin_dashboard


class AdminDashboardView(APIView):
    """Operational dashboard for PulseFit staff. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response(get_admin_dashboard())
