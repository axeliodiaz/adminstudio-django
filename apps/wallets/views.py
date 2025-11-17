"""Views for wallets app."""

from django.conf import settings
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.wallets.exceptions import PurchaseAlreadyActivatedException
from apps.wallets.models import PlanPurchase
from apps.wallets.serializers import PlanPurchaseActivateSerializer
from apps.wallets.services import WalletService


class WalletViewSet(viewsets.ViewSet):
    """ViewSet for wallet operations."""

    def activate_purchase(self, request):
        """
        Activate a plan purchase and update the user's wallet.

        This endpoint activates a PlanPurchase and applies all benefits
        to the user's Wallet. It should be called after a successful payment
        transaction (if PSP payments are enabled).

        Request body:
            {
                "purchase_id": "uuid-of-purchase"
            }

        Returns:
            - 200 OK: Purchase activated successfully
            - 400 Bad Request: Purchase already activated or invalid request
            - 404 Not Found: Purchase not found
        """
        # Check if PSP payments are enabled
        if not settings.ENABLE_PSP_PAYMENTS:
            return Response(
                {
                    "detail": "PSP payments are disabled. Enable ENABLE_PSP_PAYMENTS in settings to use this endpoint."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = PlanPurchaseActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        purchase_id = serializer.validated_data["purchase_id"]

        try:
            purchase = PlanPurchase.objects.get(id=purchase_id)
        except PlanPurchase.DoesNotExist:
            raise Http404(f"PlanPurchase with id {purchase_id} not found")

        try:
            wallet = WalletService.activate_purchase(purchase)
            return Response(
                {
                    "message": "Purchase activated successfully",
                    "wallet_id": str(wallet.id),
                    "purchase_id": str(purchase.id),
                },
                status=status.HTTP_200_OK,
            )
        except PurchaseAlreadyActivatedException as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
