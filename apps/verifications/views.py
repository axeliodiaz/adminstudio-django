import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.verifications import constants
from apps.verifications.models import VerificationCode
from apps.verifications.serializers import VerificationSerializer
from apps.verifications.services import validate_code


class VerificationView(APIView):
    authentication_classes = []
    permission_classes = []

    # Accept PATCH to verify code using UUID from URL and code from body (email not required)
    def patch(self, request, *args, **kwargs):
        serializer = VerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        verification_uuid = kwargs.get("verification_uuid")
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        try:
            vc = VerificationCode.objects.get(
                id=verification_uuid,
                code=code,
                is_removed=False,
                expires_at__gt=now,
                has_confirmed=False,
            )
        except VerificationCode.DoesNotExist:
            return Response(
                {"detail": constants.EMAIL_VERIFICATION_INVALID_CODE_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validate_code(vc)

        return Response(
            {"detail": constants.EMAIL_VERIFICATION_SUCCESS_MESSAGE}, status=status.HTTP_200_OK
        )

    # Also support PUT for idempotent verification with same logic
    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)
