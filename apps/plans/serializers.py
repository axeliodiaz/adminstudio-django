from rest_framework import serializers


class PlanPurchaseSerializer(serializers.Serializer):
    """Serializer for purchasing a plan."""

    plan_id = serializers.UUIDField(help_text="UUID of the plan to purchase")
