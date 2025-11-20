from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, help_text="Username or email")
    password = serializers.CharField(
        required=True, write_only=True, style={"input_type": "password"}
    )
