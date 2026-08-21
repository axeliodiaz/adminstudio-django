from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallets.admin_services import list_admin_purchases, list_admin_wallets


class AdminWalletListView(APIView):
    """List wallets for PulseFit staff admin."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response(
            list_admin_wallets(
                search=request.query_params.get("search"),
                status=request.query_params.get("status"),
            )
        )


class AdminPurchaseListView(APIView):
    """List plan purchases for PulseFit staff admin."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response(
            list_admin_purchases(
                search=request.query_params.get("search"),
                plan_type=request.query_params.get("type"),
            )
        )
