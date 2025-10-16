from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.members.serializers import MemberSerializer, ReservationSerializer
from apps.members.services import get_or_create_member_user, create_reservation


class MemberView(ViewSet):
    def create(self, request, *args, **kwargs):
        member_serializer = MemberSerializer(data=request.data)
        member_serializer.is_valid(raise_exception=True)
        member_schema, created = get_or_create_member_user(member_serializer.validated_data)
        data = member_schema.user.model_dump()
        if created:
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(data, status=status.HTTP_200_OK)


class ReservationView(ViewSet):
    def create(self, request, *args, **kwargs):
        serializer = ReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = create_reservation(serializer.validated_data)
        return Response(reservation.model_dump(), status=status.HTTP_201_CREATED)
