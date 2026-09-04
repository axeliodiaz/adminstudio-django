from rest_framework import serializers


class GuestPassInviteSerializer(serializers.Serializer):
    guest_name = serializers.CharField(max_length=150)
    guest_email = serializers.EmailField()
    schedule_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class GuestPassClaimSerializer(serializers.Serializer):
    waiver_accepted = serializers.BooleanField()
    spot = serializers.IntegerField(min_value=1, required=False)

    def validate_waiver_accepted(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar el consentimiento para continuar.")
        return value


class PlanPurchaseActivateSerializer(serializers.Serializer):
    """Serializer for activating a plan purchase."""

    purchase_id = serializers.UUIDField(help_text="UUID of the PlanPurchase to activate")


class WalletListQuerySerializer(serializers.Serializer):
    """Serializer for wallet list query parameters."""

    user_id = serializers.UUIDField(
        required=False, help_text="UUID of the user whose wallet to retrieve"
    )
