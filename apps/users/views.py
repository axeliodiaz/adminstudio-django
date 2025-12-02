from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_expiring_token.models import ExpiringToken

from apps.users.serializers import LoginSerializer, ChangePasswordSerializer
from apps.users.schemas import UserSchema
from apps.users.services import change_user_password


class LoginView(APIView):
    """
    Endpoint to authenticate users.

    Accepts username/email and password, and returns an authentication token
    along with serialized user data.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Intentar obtener usuario por username o email
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return Response(
                    {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
                )

        # Verificar si el usuario está activo antes de verificar la contraseña
        if not user.is_active:
            return Response(
                {"detail": "User account is disabled."}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Verificar la contraseña
        if not user.check_password(password):
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        # Regenerar siempre el token en cada login:
        # eliminamos cualquier token previo y creamos uno nuevo y válido.
        ExpiringToken.objects.filter(user=user).delete()
        token = ExpiringToken.objects.create(user=user)

        # Serializar datos del usuario
        user_data = UserSchema.model_validate(user).model_dump()

        return Response(
            {
                "token": token.key,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    Endpoint to change the authenticated user's password.

    Requires the current password and the new password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        try:
            change_user_password(request.user, old_password, new_password)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
