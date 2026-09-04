"""Views for wallets app."""

from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model

from apps.wallets.exceptions import PurchaseAlreadyActivatedException
from apps.wallets.models import GuestPassInvitation, PlanPurchase, Wallet
from apps.wallets.schemas import PlanPurchaseSchema, WalletDashboardSchema, WalletSchema
from apps.wallets.serializers import (
    GuestPassClaimSerializer,
    GuestPassInviteSerializer,
    PlanPurchaseActivateSerializer,
    WalletListQuerySerializer,
)
from apps.wallets.services import WalletService

User = get_user_model()


def _guest_pass_payload(invitation):
    schedule = invitation.schedule
    issuer = invitation.issuer
    return {
        "id": str(invitation.id),
        "guest_name": invitation.guest_name,
        "guest_email": invitation.guest_email,
        "message": invitation.message,
        "token": invitation.token,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "schedule_id": str(invitation.schedule_id) if invitation.schedule_id else None,
        "schedule_title": getattr(schedule, "title", None),
        "issuer_name": issuer.get_full_name() or issuer.username,
        "claimed_at": invitation.claimed_at,
        "reservation_id": str(invitation.reservation_id) if invitation.reservation_id else None,
    }


class GuestPassInviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GuestPassInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["guest_email"].lower() == request.user.email.lower():
            return Response(
                {"detail": "No puedes invitarte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST
            )
        schedule_id = data.get("schedule_id")
        if schedule_id:
            from apps.schedules.models import Schedule

            if not Schedule.objects.filter(id=schedule_id, is_removed=False).exists():
                return Response(
                    {"detail": "La clase no existe."}, status=status.HTTP_400_BAD_REQUEST
                )
        invitation = GuestPassInvitation.objects.create(
            issuer=request.user,
            guest_name=data["guest_name"],
            guest_email=data["guest_email"].lower(),
            schedule_id=schedule_id,
            message=data.get("message", ""),
            expires_at=timezone.now() + timedelta(days=14),
        )
        payload = _guest_pass_payload(invitation)
        frontend_url = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip(
            "/"
        )
        payload["claim_url"] = f"{frontend_url}/#guest-pass/{invitation.token}"
        return Response(payload, status=status.HTTP_201_CREATED)


class GuestPassHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        WalletService.expire_guest_passes()
        invitations = GuestPassInvitation.objects.filter(issuer=request.user).select_related(
            "schedule", "issuer"
        )
        return Response([_guest_pass_payload(invitation) for invitation in invitations])


class GuestPassClaimView(APIView):
    """Preview a guest pass publicly and claim/book it after authentication."""

    permission_classes = [AllowAny]

    def get(self, request, token):
        WalletService.expire_guest_passes()
        invitation = (
            GuestPassInvitation.objects.select_related("schedule", "issuer")
            .filter(token=token)
            .first()
        )
        if not invitation:
            raise Http404("Guest pass not found")
        payload = _guest_pass_payload(invitation)
        payload.pop("guest_email", None)
        return Response(payload)

    def post(self, request, token):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Debes iniciar sesión para reclamar este pase."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = GuestPassClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        WalletService.expire_guest_passes()
        try:
            invitation = GuestPassInvitation.objects.select_related("schedule", "issuer").get(
                token=token
            )
        except GuestPassInvitation.DoesNotExist:
            raise Http404("Guest pass not found")
        if invitation.status in {
            GuestPassInvitation.Status.EXPIRED,
            GuestPassInvitation.Status.CANCELLED,
        }:
            return Response(
                {"detail": "Este pase de invitado venció."}, status=status.HTTP_400_BAD_REQUEST
            )
        if request.user.email.lower() != invitation.guest_email.lower():
            return Response(
                {"detail": "Este pase fue enviado a otro correo."}, status=status.HTTP_403_FORBIDDEN
            )
        if invitation.claimed_by_id and invitation.claimed_by_id != request.user.id:
            return Response(
                {"detail": "Este pase ya fue reclamado."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not invitation.claimed_by_id:
            from apps.legal.models import LegalDocument, LegalDocumentType

            waiver = (
                LegalDocument.objects.filter(
                    document_type=LegalDocumentType.WAIVER, is_published=True, is_removed=False
                )
                .order_by("-effective_date", "-created")
                .first()
            )
            invitation.claimed_by = request.user
            invitation.claimed_at = timezone.now()
            invitation.waiver_accepted_at = timezone.now()
            invitation.waiver_version = waiver.version if waiver else "basic-consent"
            invitation.status = GuestPassInvitation.Status.CLAIMED
            invitation.save(
                update_fields=[
                    "claimed_by",
                    "claimed_at",
                    "waiver_accepted_at",
                    "waiver_version",
                    "status",
                    "modified",
                ]
            )
        if (
            invitation.schedule_id
            and serializer.validated_data.get("spot")
            and not invitation.reservation_id
        ):
            from apps.members.members import create_reservation

            reservation = create_reservation(
                {
                    "user_id": request.user.id,
                    "schedule_id": invitation.schedule_id,
                    "spot": serializer.validated_data["spot"],
                    "guest_pass": invitation,
                }
            )
            return Response(
                {**_guest_pass_payload(invitation), "reservation_id": str(reservation.id)},
                status=status.HTTP_201_CREATED,
            )
        return Response(_guest_pass_payload(invitation))


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
