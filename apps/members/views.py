from datetime import date

from pydantic import ValidationError as PydanticValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from apps.members import constants
from apps.members.exceptions import (
    InvalidSpotException,
    RoomFullException,
    ReservationInvalidStateException,
)
from apps.members.schemas import AdminMemberCreateSchema, AdminMemberUpdateSchema
from apps.members.serializers import (
    MemberSerializer,
    ReservationSerializer,
    ReservationListQuerySerializer,
    ReservationChangeSpotSerializer,
    ReservationCancelSerializer,
)
from apps.members.services import (
    create_admin_member,
    get_admin_member,
    get_or_create_member_user,
    get_member_from_user_id,
    create_reservation,
    cancel_reservation,
    change_reservation_spot,
    list_admin_members,
    list_reservations,
    update_admin_member,
)
from apps.members.models import Member, Reservation


def _pydantic_error_response(exc: PydanticValidationError) -> Response:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(part) for part in first.get("loc", [])) or "payload"
    return Response(
        {"detail": f"{loc}: {first.get('msg', 'Datos inválidos.')}"},
        status=status.HTTP_400_BAD_REQUEST,
    )


class MemberView(ViewSet):
    permission_classes = [AllowAny]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        get_member action requires authentication.
        """
        if self.action == "get_member":
            return [IsAuthenticated()]
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        member_serializer = MemberSerializer(data=request.data)
        member_serializer.is_valid(raise_exception=True)
        member_schema, created = get_or_create_member_user(member_serializer.validated_data)
        data = member_schema.user.model_dump()
        if created:
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(data, status=status.HTTP_200_OK)

    def get_member(self, request, *args, **kwargs):
        try:
            member_schema = get_member_from_user_id(request.user.id)
            return Response(member_schema.model_dump(), status=status.HTTP_200_OK)
        except Member.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


class ReservationView(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = ReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data.copy()
        validated_data["user_id"] = request.user.id
        try:
            reservation = create_reservation(validated_data)
        except RoomFullException as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except InvalidSpotException as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(reservation.model_dump(), status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        has_start_date = "start_date" in query_params
        has_end_date = "end_date" in query_params
        data = query_params.copy()

        member = Member.objects.filter(user=request.user).first()
        if not member:
            return Response([], status=status.HTTP_200_OK)

        data["member_id"] = str(member.id)

        if not has_start_date:
            today = date.today()
            data["start_date"] = today.isoformat()

        if not has_end_date:
            data["end_date"] = date(2100, 1, 1).isoformat()

        query_serializer = ReservationListQuerySerializer(data=data)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data
        schemas = list_reservations(data)
        payload = [schema.model_dump() for schema in schemas]
        return Response(payload, status=status.HTTP_200_OK)

    def cancel(self, request, *args, **kwargs):
        serializer = ReservationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation_id = serializer.validated_data["reservation_id"]
        try:
            reservation = cancel_reservation(reservation_id)
        except Reservation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except ReservationInvalidStateException as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "message": constants.RESERVATION_CANCELLED_SUCCESS_MESSAGE,
                **reservation.model_dump(),
            },
            status=status.HTTP_200_OK,
        )

    def change_spot(self, request, schedule_id=None, *args, **kwargs):
        serializer = ReservationChangeSpotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reservation = change_reservation_spot(
                schedule_id, str(request.user.id), serializer.validated_data["new_spot"]
            )
        except Reservation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except (ReservationInvalidStateException, InvalidSpotException) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(reservation.model_dump(), status=status.HTTP_200_OK)


class AdminMemberListView(APIView):
    """List or create members for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        members_list = list_admin_members(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
        )
        return Response(members_list, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            payload = AdminMemberCreateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            member, created = create_admin_member(data=payload.model_dump())
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            member,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AdminMemberDetailView(APIView):
    """Retrieve or update a member for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]
    http_method_names = ["get", "patch", "head", "options"]

    def get(self, request, member_id, *args, **kwargs):
        return Response(get_admin_member(member_id=member_id), status=status.HTTP_200_OK)

    def patch(self, request, member_id, *args, **kwargs):
        try:
            payload = AdminMemberUpdateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            member = update_admin_member(
                member_id=member_id,
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(member, status=status.HTTP_200_OK)
