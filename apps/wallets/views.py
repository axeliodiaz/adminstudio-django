"""Views for wallets app."""

from django.conf import settings
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.response import Response

from django.contrib.auth import get_user_model

from apps.wallets.exceptions import PurchaseAlreadyActivatedException
from apps.wallets.models import PlanPurchase, Wallet
from apps.wallets.schemas import PlanPurchaseSchema, WalletDashboardSchema, WalletSchema
from apps.wallets.serializers import PlanPurchaseActivateSerializer, WalletListQuerySerializer
from apps.wallets.services import WalletService

User = get_user_model()


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
        serializer = PlanPurchaseActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        purchase_id = serializer.validated_data["purchase_id"]

        try:
            purchase = PlanPurchase.objects.get(id=purchase_id)
        except PlanPurchase.DoesNotExist:
            raise Http404(f"PlanPurchase with id {purchase_id} not found")

        try:
            wallet = WalletService.activate_purchase(purchase)
        except PurchaseAlreadyActivatedException as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = "Purchase activated successfully"
        # Check if PSP payments are enabled
        if not settings.ENABLE_PSP_PAYMENTS:
            message += " (With PSP payments disabled)"
        return Response(
            {
                "message": message,
                "wallet_id": str(wallet.id),
                "purchase_id": str(purchase.id),
            },
            status=status.HTTP_200_OK,
        )

    def list(self, request):
        """
        Get wallet data for a user.

        Query parameters:
            - user_id (optional): UUID of the user whose wallet to retrieve.
              If not provided, returns the wallet of the authenticated user.
              Only staff/superuser can view other users' wallets.

        Returns comprehensive wallet information including:
        - Wallet balance (class credits, guest pass credits)
        - Membership status and expiration date
        - Active benefits (priority booking, freeze membership, etc.)
        - Purchase history (all plan purchases)

        Returns:
            - 200 OK: Wallet data
            - 400 Bad Request: Invalid user_id or permission denied
            - 404 Not Found: User not found
        """
        # Validate query parameters
        query_serializer = WalletListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        authenticated_user = request.user

        # Check if user is authenticated (not AnonymousUser)
        if not authenticated_user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = query_serializer.validated_data.get("user_id")

        # Determine which user's wallet to retrieve
        if user_id:
            # If user_id is provided, check permissions
            if not (authenticated_user.is_staff or authenticated_user.is_superuser):
                return Response(
                    {"detail": "You do not have permission to view other users' wallets."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": f"User with id {user_id} not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            user = target_user
        else:
            # If no user_id provided, use authenticated user
            user = authenticated_user

        # Get or create wallet for the user
        wallet, _ = Wallet.objects.get_or_create(user=user)

        # Get all purchases for the user, ordered by most recent first
        purchases = (
            PlanPurchase.objects.filter(user=user).select_related("plan").order_by("-created")
        )

        # Serialize purchases with plan name
        purchase_schemas = []
        for purchase in purchases:
            purchase_data = {
                "id": purchase.id,
                "created": purchase.created,
                "modified": purchase.modified,
                "price_paid": purchase.price_paid,
                "activated_since": purchase.activated_since,
                "start": purchase.start,
                "end": purchase.end,
                "plan_id": purchase.plan.id,
                "plan_name": purchase.plan.name,
            }
            purchase_schemas.append(PlanPurchaseSchema(**purchase_data))

        # Create dashboard schema
        wallet_schema = WalletSchema.model_validate(wallet)
        dashboard_data = WalletDashboardSchema(
            wallet=wallet_schema,
            purchases=purchase_schemas,
        )

        return Response(
            dashboard_data.model_dump(by_alias=True),
            status=status.HTTP_200_OK,
        )
