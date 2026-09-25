from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallets.admin_cache import get_or_compute, invalidate
from apps.wallets.admin_services import list_admin_purchases, list_admin_wallets


class AdminWalletListView(APIView):
    """List wallets for PulseFit staff admin. Cached ~5 min per filter set (CYC-116)."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        params = {
            "search": request.query_params.get("search"),
            "status": request.query_params.get("status"),
        }
        return Response(get_or_compute("wallets", params, lambda: list_admin_wallets(**params)))


class AdminPurchaseListView(APIView):
    """List plan purchases for PulseFit staff admin. Cached ~5 min per filter set (CYC-116)."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        params = {
            "search": request.query_params.get("search"),
            "plan_type": request.query_params.get("type"),
        }
        return Response(get_or_compute("purchases", params, lambda: list_admin_purchases(**params)))


class AdminWalletCacheRefreshView(APIView):
    """Invalidate the cached wallets/purchases payloads. Staff only (CYC-116).

    The Billeteras y compras reload button calls this endpoint and then
    refetches, so the lists re-query the database and rebuild the cache.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, *args, **kwargs):
        invalidate()
        return Response({"detail": "Wallets cache invalidated."})
