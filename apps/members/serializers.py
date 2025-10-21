from rest_framework import serializers


class MemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    created = serializers.DateTimeField(read_only=True)


class ReservationSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    schedule_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ReservationListQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    member_id = serializers.UUIDField(required=False)
    schedule__instructor_id = serializers.UUIDField(required=False)
    schedule__room_id = serializers.UUIDField(required=False)
