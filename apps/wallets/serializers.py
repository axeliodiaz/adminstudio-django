from rest_framework import serializers


class PlanPurchaseActivateSerializer(serializers.Serializer):
    """Serializer for activating a plan purchase."""

    purchase_id = serializers.UUIDField(help_text="UUID of the PlanPurchase to activate")
