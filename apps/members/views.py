from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.members.exceptions import (
    InvalidSpotException,
    RoomFullException,
    ReservationInvalidStateException,
)
from apps.members.serializers import (
    MemberSerializer,
    ReservationSerializer,
    ReservationListQuerySerializer,
)
from apps.members.services import (
    get_or_create_member_user,
    create_reservation,
    cancel_reservation,
    list_reservations,
)
from apps.members.models import Reservation


class MemberView(ViewSet):
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        member_serializer = MemberSerializer(data=request.data)
        member_serializer.is_valid(raise_exception=True)
        member_schema, created = get_or_create_member_user(member_serializer.validated_data)
        data = member_schema.user.model_dump()
        if created:
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(data, status=status.HTTP_200_OK)


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
        query_serializer = ReservationListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data
        schemas = list_reservations(data)
        payload = [schema.model_dump() for schema in schemas]
        return Response(payload, status=status.HTTP_200_OK)

    def cancel(self, request, pk=None, *args, **kwargs):
        try:
            reservation = cancel_reservation(pk)
        except Reservation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except ReservationInvalidStateException as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(reservation.model_dump(), status=status.HTTP_200_OK)
