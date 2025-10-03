from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.schedules.models import Schedule
from apps.schedules.serializers import ScheduleCreateSerializer, ScheduleSerializer
from apps.schedules.services import create_schedule, get_schedule_schema_list

from django.utils.dateparse import parse_datetime


class ScheduleViewSet(viewsets.ViewSet):
    """Minimal viewset for schedules: list, retrieve, create."""

    def list(self, request):
        start_time_str = request.query_params.get("start_time")
        start_time = None
        if start_time_str:
            start_time = parse_datetime(start_time_str)
            if start_time is None:
                return Response(
                    {
                        "detail": "Invalid start_time format. Use ISO 8601, e.g. 2025-10-03T13:57:00Z."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Use service-layer query and schema conversion
        schemas = get_schedule_schema_list(start_time=start_time)
        data = [s.model_dump() for s in schemas]
        return Response(data)

    def retrieve(self, request, pk=None):
        schedule = Schedule.objects.get(pk=pk)
        data = ScheduleSerializer(schedule).data
        return Response(data)

    def create(self, request):
        serializer = ScheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule_schema = create_schedule(**serializer.validated_data)
        return Response(schedule_schema.model_dump(), status=status.HTTP_201_CREATED)
