from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.referrals import services


class ReferralClickView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        code = str(request.data.get("code", "")).strip()
        if not code:
            return Response(
                {"detail": "El código de referido es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            services.record_click(code=code, user=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyReferralView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(services.referral_dashboard(user=request.user), status=status.HTTP_200_OK)


class ReferralAdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response(services.admin_dashboard(), status=status.HTTP_200_OK)
