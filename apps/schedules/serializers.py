"""Serializers for schedules app.

Input serializer for creation and output serializer mirroring ScheduleSchema.
"""

from rest_framework import serializers

from apps.schedules import constants


class ScheduleCreateSerializer(serializers.Serializer):
    instructor_id = serializers.UUIDField()
    start_time = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=1)
    room_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=constants.SCHEDULE_STATUSES)


class ScheduleSerializer(ScheduleCreateSerializer):
    id = serializers.UUIDField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    instructor = serializers.UUIDField(source="instructor_id", read_only=True)
    room = serializers.UUIDField(source="room_id", read_only=True)
    status = serializers.ChoiceField(
        choices=[
            constants.SCHEDULE_STATUS_DRAFT,
            constants.SCHEDULE_STATUS_SCHEDULED,
            constants.SCHEDULE_STATUS_COMPLETED,
            constants.SCHEDULE_STATUS_CANCELED,
        ]
    )
