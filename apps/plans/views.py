"""Views for plans app using services layer and Pydantic schemas."""

from decimal import Decimal
from typing import Any

from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.plans import services
from apps.plans.models import Plan
from apps.plans.serializers import PlanPurchaseSerializer
from apps.wallets.models import PlanPurchase
from apps.wallets.schemas import PlanPurchaseSchema


class PlanViewSet(viewsets.ViewSet):
    """List and retrieve plans leveraging the services module.

    These endpoints are public and do not require authentication.
    The purchase endpoint requires authentication.
    """

    permission_classes = [AllowAny]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Purchase action requires authentication.
        """
        if self.action == "purchase":
            return [IsAuthenticated()]
        return [AllowAny()]

    def list(self, request, *args: Any, **kwargs: Any) -> Response:
        schemas = services.get_plans()
        data = [s.model_dump(by_alias=True) for s in schemas]
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk: str | None = None, *args: Any, **kwargs: Any) -> Response:
        try:
            schema = services.get_plan_by_id(pk)
        except Plan.DoesNotExist as exc:
            raise Http404 from exc
        data = schema.model_dump(by_alias=True)
        return Response(data, status=status.HTTP_200_OK)

    def purchase(self, request, *args: Any, **kwargs: Any) -> Response:
        """
        Purchase a plan by creating a PlanPurchase record.

        This endpoint creates a PlanPurchase with activated_since=None.
        After successful payment processing (if PSP payments are enabled),
        the purchase should be activated using the activate-purchase endpoint.

        Request body:
            {
                "plan_id": "uuid-of-plan"
            }

        Returns:
            - 201 Created: Purchase created successfully
            - 400 Bad Request: Invalid plan_id or plan is not active
            - 404 Not Found: Plan not found
        """
        serializer = PlanPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = serializer.validated_data["plan_id"]

        try:
            plan = Plan.objects.get(id=plan_id, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {"detail": f"Active plan with id {plan_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create the purchase
        purchase = PlanPurchase.objects.create(
            user=request.user,
            plan=plan,
            price_paid=Decimal(str(plan.price)),
            activated_since=None,
        )

        # Serialize the purchase
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
        purchase_schema = PlanPurchaseSchema(**purchase_data)

        return Response(
            purchase_schema.model_dump(by_alias=True),
            status=status.HTTP_201_CREATED,
        )
