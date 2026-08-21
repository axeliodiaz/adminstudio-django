from rest_framework import serializers


class PlanPurchaseActivateSerializer(serializers.Serializer):
    """Serializer for activating a plan purchase."""

    purchase_id = serializers.UUIDField(help_text="UUID of the PlanPurchase to activate")


class WalletListQuerySerializer(serializers.Serializer):
    """Serializer for wallet list query parameters."""

    user_id = serializers.UUIDField(
        required=False, help_text="UUID of the user whose wallet to retrieve"
    )
