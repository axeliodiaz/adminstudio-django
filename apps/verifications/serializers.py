from rest_framework import serializers


class VerificationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    # UUID now comes from URL, keep optional for backward compatibility
    verification_code_uuid = serializers.UUIDField(required=False)
    # Email is optional for now; included for potential future cross-checks
    email = serializers.EmailField(required=False)

    def validate_code(self, value: str) -> str:
        # Ensure code is exactly 6 digits/alphanum depending on business rules.
        # Keeping it minimal: strip spaces.
        return value.strip()
