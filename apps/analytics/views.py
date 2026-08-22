from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.constants import DASHBOARD_ALLOWED_DAYS, DASHBOARD_DEFAULT_DAYS
from apps.analytics.member_stats import get_member_stats
from apps.analytics.services import get_admin_dashboard

User = get_user_model()


class MemberStatsView(APIView):
    """Activity dashboard stats for the authenticated member."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(get_member_stats(request.user))


class AdminMemberStatsView(APIView):
    """Activity dashboard stats for a given user. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id, is_removed=False)
        return Response(get_member_stats(user))


class AdminDashboardView(APIView):
    """Operational dashboard for PulseFit staff. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response(get_admin_dashboard(days=_parse_days(request.query_params.get("days"))))


def _parse_days(raw) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return DASHBOARD_DEFAULT_DAYS
    if days not in DASHBOARD_ALLOWED_DAYS:
        return DASHBOARD_DEFAULT_DAYS
    return days
