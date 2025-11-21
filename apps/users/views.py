from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_expiring_token.models import ExpiringToken

from apps.users.serializers import LoginSerializer
from apps.users.schemas import UserSchema


class LoginView(APIView):
    """
    Endpoint para autenticar usuarios.
    Recibe username/email y password, devuelve un token de autenticación.
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

        # Obtener o crear token (el paquete maneja la expiración automáticamente)
        token, created = ExpiringToken.objects.get_or_create(user=user)

        # Serializar datos del usuario
        user_data = UserSchema.model_validate(user).model_dump()

        return Response(
            {
                "token": token.key,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )
