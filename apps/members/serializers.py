from rest_framework import serializers

from apps.schedules.schedules import get_schedule_by_id


class MemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    created = serializers.DateTimeField(read_only=True)


class ReservationSerializer(serializers.Serializer):
    schedule_id = serializers.UUIDField()
    spot = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        """Validate that spot is within the room's capacity range."""
        schedule_id = attrs.get("schedule_id")
        spot = attrs.get("spot")

        if schedule_id and spot is not None:
            schedule = get_schedule_by_id(schedule_id)
            room_capacity = schedule.room.capacity

            if spot < 1:
                raise serializers.ValidationError(
                    {"spot": "Spot must be greater than or equal to 1."}
                )
            if spot > room_capacity:
                raise serializers.ValidationError(
                    {
                        "spot": f"Spot must be less than or equal to the room capacity ({room_capacity})."
                    }
                )

        return attrs


class ReservationListQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    member_id = serializers.UUIDField(required=False)
    schedule__instructor_id = serializers.UUIDField(required=False)
    schedule__room_id = serializers.UUIDField(required=False)
