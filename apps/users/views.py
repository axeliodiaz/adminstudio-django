from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_expiring_token.models import ExpiringToken

from apps.users import constants
from apps.users.serializers import (
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordRecoveryRequestSerializer,
    PasswordRecoveryConfirmSerializer,
    EmailChangeRequestSerializer,
    EmailChangeConfirmSerializer,
)
from pydantic import ValidationError as PydanticValidationError

from apps.users.schemas import AdminUserUpdateSchema, CurrentUserSchema
from apps.users.services import (
    change_user_password,
    request_password_recovery,
    confirm_password_reset,
    get_admin_user,
    list_admin_users,
    request_admin_password_recovery,
    update_admin_user,
    request_admin_email_change,
    confirm_email_change,
)


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

        user_data = CurrentUserSchema.model_validate(user).model_dump(mode="json")

        return Response(
            {
                "token": token.key,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserView(APIView):
    """Return the authenticated user, including staff flags."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_data = CurrentUserSchema.model_validate(request.user).model_dump(mode="json")
        return Response(user_data, status=status.HTTP_200_OK)


class AdminUserListView(APIView):
    """List users for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        users = list_admin_users(
            search=request.query_params.get("search"),
            role=request.query_params.get("role"),
        )
        return Response(users, status=status.HTTP_200_OK)


class AdminUserDetailView(APIView):
    """Retrieve or update a user for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = get_admin_user(user_id=user_id, actor=request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(user, status=status.HTTP_200_OK)

    def patch(self, request, user_id, *args, **kwargs):
        try:
            payload = AdminUserUpdateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            first = exc.errors()[0] if exc.errors() else {}
            loc = ".".join(str(part) for part in first.get("loc", [])) or "payload"
            return Response(
                {"detail": f"{loc}: {first.get('msg', 'Datos inválidos.')}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = payload.model_dump(exclude_unset=True)
        try:
            user = update_admin_user(user_id=user_id, data=data, actor=request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(user, status=status.HTTP_200_OK)


class AdminUserPasswordRecoveryView(APIView):
    """Send a password recovery email for a user. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id, *args, **kwargs):
        try:
            request_admin_password_recovery(user_id=user_id, actor=request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": constants.PASSWORD_RECOVERY_ADMIN_SUCCESS_MESSAGE},
            status=status.HTTP_200_OK,
        )


class AdminUserEmailChangeView(APIView):
    """Request an email change for a user. Staff only. The user must confirm by email."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id, *args, **kwargs):
        serializer = EmailChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            pending_email = request_admin_email_change(
                user_id=user_id,
                email=serializer.validated_data["email"],
                actor=request.user,
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "detail": constants.EMAIL_CHANGE_ADMIN_SUCCESS_MESSAGE,
                "pending_email": pending_email,
            },
            status=status.HTTP_200_OK,
        )


class EmailChangeConfirmView(APIView):
    """Confirm a staff-requested email change from the mailed link."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def patch(self, request, change_uuid, *args, **kwargs):
        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_email_change(change_uuid, serializer.validated_data["code"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": constants.EMAIL_CHANGE_CONFIRM_SUCCESS_MESSAGE},
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)


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
        return Response({"detail": "Contraseña actualizada."}, status=status.HTTP_200_OK)


class PasswordRecoveryRequestView(APIView):
    """
    Endpoint to request password recovery.

    Accepts an email address and sends a recovery code via email.
    For security, always returns success even if the email doesn't exist.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordRecoveryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        request_password_recovery(email)

        return Response(
            {"detail": constants.PASSWORD_RECOVERY_REQUEST_SUCCESS_MESSAGE},
            status=status.HTTP_200_OK,
        )


class PasswordRecoveryConfirmView(APIView):
    """
    Endpoint to confirm password recovery and set new password.

    Accepts a recovery code and new password, validates the code,
    and updates the user's password.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordRecoveryConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        try:
            confirm_password_reset(code, new_password)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": constants.PASSWORD_RECOVERY_CONFIRM_SUCCESS_MESSAGE},
            status=status.HTTP_200_OK,
        )
