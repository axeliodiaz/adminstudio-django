from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, help_text="Username or email")
    password = serializers.CharField(
        required=True, write_only=True, style={"input_type": "password"}
    )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="Current password",
    )
    new_password = serializers.CharField(
        required=True, write_only=True, style={"input_type": "password"}, help_text="New password"
    )


class PasswordRecoveryRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Email address of the user")


class PasswordRecoveryConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text="6-character recovery code",
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="New password",
    )

    def validate_code(self, value: str) -> str:
        """Strip whitespace from code."""
        return value.strip().upper()
