from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.members.services import list_reservations
from apps.schedules.models import Schedule
from apps.schedules.serializers import ScheduleCreateSerializer
from apps.schedules.services import (
    create_admin_schedule,
    create_schedule,
    delete_admin_schedule,
    get_admin_schedule,
    get_schedule_schema_by_id,
    get_schedule_schema_list,
    list_admin_schedules,
    update_admin_schedule,
)

from datetime import datetime, time, timedelta

from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import get_default_timezone, make_aware
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError
from rest_framework.views import APIView

from apps.schedules.schemas import AdminScheduleWriteSchema


def _pydantic_error_response(exc: PydanticValidationError) -> Response:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(part) for part in first.get("loc", [])) or "payload"
    return Response(
        {"detail": f"{loc}: {first.get('msg', 'Datos inválidos.')}"},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _parse_datetime_param(value: str | None, field_name: str):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return Response(
            {"detail": (f"Invalid {field_name} format. Use ISO 8601, e.g. 2025-10-03T13:57:00Z.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return parsed


def _parse_date_param(value: str | None, field_name: str):
    if not value:
        return None
    parsed = parse_date(value)
    if parsed is None:
        return Response(
            {"detail": f"Invalid {field_name} format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return parsed


def _aware_day_start(day) -> datetime:
    tz = get_default_timezone()
    return make_aware(datetime.combine(day, time.min), tz)


def _bounds_from_dates(start_date, end_date) -> tuple[datetime | None, datetime | None]:
    start_bound = _aware_day_start(start_date) if start_date else None
    if end_date:
        end_bound = _aware_day_start(end_date) + timedelta(days=1) - timedelta(microseconds=1)
    else:
        end_bound = None
    return start_bound, end_bound


def _parse_uuid_list(request, field_name: str):
    values: list[UUID] = []
    for raw in request.query_params.getlist(field_name):
        for part in str(raw).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                values.append(UUID(part))
            except (ValueError, TypeError):
                return Response(
                    {"detail": f"Invalid {field_name} format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
    return values


class ScheduleViewSet(viewsets.ViewSet):
    """Minimal viewset for schedules: list, retrieve, create."""

    permission_classes = [AllowAny]

    def _get_start_time_params(self, start_time: str | None = None):
        parsed = _parse_datetime_param(start_time, "start_time")
        if isinstance(parsed, Response):
            return parsed
        return parsed

    def list(self, request):
        start_time = self._get_start_time_params(request.query_params.get("start_time"))
        if isinstance(start_time, Response):
            return start_time
        end_time = _parse_datetime_param(request.query_params.get("end_time"), "end_time")
        if isinstance(end_time, Response):
            return end_time
        start_date = _parse_date_param(request.query_params.get("start_date"), "start_date")
        if isinstance(start_date, Response):
            return start_date
        end_date = _parse_date_param(request.query_params.get("end_date"), "end_date")
        if isinstance(end_date, Response):
            return end_date

        date_start, date_end = _bounds_from_dates(start_date, end_date)
        if start_time is None:
            start_time = date_start
        elif date_start is not None:
            start_time = max(start_time, date_start)
        if end_time is None:
            end_time = date_end
        elif date_end is not None:
            end_time = min(end_time, date_end)

        instructor_ids = _parse_uuid_list(request, "instructor_id")
        if isinstance(instructor_ids, Response):
            return instructor_ids
        room_ids = _parse_uuid_list(request, "room_id")
        if isinstance(room_ids, Response):
            return room_ids

        class_types = [
            part.strip()
            for raw in request.query_params.getlist("class_type")
            for part in str(raw).split(",")
            if part.strip()
        ]

        schemas = get_schedule_schema_list(
            start_time=start_time,
            end_time=end_time,
            instructor_ids=instructor_ids or None,
            room_name=request.query_params.get("room_name"),
            room_ids=room_ids or None,
            title=request.query_params.get("title"),
            titles=class_types or None,
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


class AdminScheduleListView(APIView):
    """List or create class schedules for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        start_time = _parse_datetime_param(request.query_params.get("start_time"), "start_time")
        if isinstance(start_time, Response):
            return start_time
        end_time = _parse_datetime_param(request.query_params.get("end_time"), "end_time")
        if isinstance(end_time, Response):
            return end_time

        schedules = list_admin_schedules(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
            instructor_id=request.query_params.get("instructor_id"),
            room_id=request.query_params.get("room_id"),
            start_time=start_time,
            end_time=end_time,
        )
        return Response(schedules, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            payload = AdminScheduleWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            schedule = create_admin_schedule(data=payload.model_dump(exclude_unset=True))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(schedule, status=status.HTTP_201_CREATED)


class AdminScheduleDetailView(APIView):
    """Retrieve, update, or delete a class schedule. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, schedule_id, *args, **kwargs):
        return Response(get_admin_schedule(schedule_id=schedule_id), status=status.HTTP_200_OK)

    def patch(self, request, schedule_id, *args, **kwargs):
        try:
            payload = AdminScheduleWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            schedule = update_admin_schedule(
                schedule_id=schedule_id,
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(schedule, status=status.HTTP_200_OK)

    def delete(self, request, schedule_id, *args, **kwargs):
        try:
            delete_admin_schedule(schedule_id=schedule_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
