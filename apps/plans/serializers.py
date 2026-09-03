from rest_framework import serializers


class PlanPurchaseSerializer(serializers.Serializer):
    """Serializer for purchasing a plan."""

    plan_id = serializers.UUIDField(help_text="UUID of the plan to purchase")
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)
    promo_code = serializers.CharField(required=False, allow_blank=True, max_length=40)
    payment_method = serializers.CharField(required=False, allow_blank=True, max_length=32)


class CheckoutItemSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class GiftRecipientSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    message = serializers.CharField(max_length=1_000, required=False, allow_blank=True)
    send_at = serializers.DateTimeField(required=False)


class CheckoutSerializer(serializers.Serializer):
    items = CheckoutItemSerializer(many=True)
    promo_code = serializers.CharField(required=False, allow_blank=True, max_length=40)
    payment_method = serializers.CharField(required=False, allow_blank=True, max_length=32)
    accept_terms = serializers.BooleanField()
    gift_recipient = GiftRecipientSerializer(required=False)

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar los términos y condiciones.")
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("El carrito está vacío.")
        return value


class ValidatePromoSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    plan_id = serializers.UUIDField(required=False)
    subtotal = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)


class RedeemGiftCardSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)
