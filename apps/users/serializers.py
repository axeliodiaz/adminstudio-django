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
