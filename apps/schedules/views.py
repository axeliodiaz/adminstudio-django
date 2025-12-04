from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.members.services import list_reservations
from apps.schedules.models import Schedule
from apps.schedules.serializers import ScheduleCreateSerializer, ScheduleSerializer
from apps.schedules.services import (
    create_schedule,
    get_schedule_schema_by_id,
    get_schedule_schema_list,
)

from django.utils.dateparse import parse_datetime
from uuid import UUID


class ScheduleViewSet(viewsets.ViewSet):
    """Minimal viewset for schedules: list, retrieve, create."""

    permission_classes = [AllowAny]

    def _get_start_time_params(self, start_time: str | None = None):
        if start_time:
            start_time = parse_datetime(start_time)
            if start_time is None:
                return Response(
                    {
                        "detail": "Invalid start_time format. Use ISO 8601, e.g. 2025-10-03T13:57:00Z."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return start_time

    def list(self, request):
        start_time_str = request.query_params.get("start_time")
        start_time = self._get_start_time_params(start_time_str)
        if isinstance(start_time, Response):
            return start_time
        instructor_id = request.query_params.get("instructor_id")
        room_name = request.query_params.get("room_name")
        schemas = get_schedule_schema_list(
            start_time=start_time,
            instructor_id=instructor_id,
            room_name=room_name,
        )
        data = [s.model_dump() for s in schemas]
        return Response(data)

    def retrieve(self, request, pk=None):
        # Validate that pk is a valid UUID
        try:
            UUID(str(pk))
        except (ValueError, TypeError):
            return Response(
                {"detail": f'"{pk}" is not a valid UUID.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            schedule_schema = get_schedule_schema_by_id(pk)
        except Schedule.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        # Convert schema to dict and adjust field names to match serializer output
        data = schedule_schema.model_dump()
        # Map instructor_id -> instructor and room_id -> room to match serializer
        data["instructor"] = str(data.pop("instructor_id"))
        data["room"] = str(data.pop("room_id"))
        return Response(data)

    def create(self, request):
        serializer = ScheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule_schema = create_schedule(**serializer.validated_data)
        return Response(schedule_schema.model_dump(), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="reservations")
    def reservations(self, request, pk=None):
        """List reservations for a specific schedule."""
        # Validate that pk is a valid UUID
        try:
            UUID(str(pk))
        except (ValueError, TypeError):
            return Response(
                {"detail": f'"{pk}" is not a valid UUID.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            schedule_schema = get_schedule_schema_by_id(pk)
        except Schedule.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Use the list_reservations service with schedule_id filter
        reservation_schemas = list_reservations({"schedule_id": str(schedule_schema.id)})
        data = [schema.model_dump() for schema in reservation_schemas]
        return Response(data, status=status.HTTP_200_OK)
