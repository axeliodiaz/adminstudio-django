from rest_framework import serializers
from uuid import UUID


class ProfileSerializer(serializers.Serializer):
    """
    Serializer plano para validar los datos que se escriben en el perfil.
    La persistencia real se hace en apps.users.services sobre el modelo User.
    """

    # Personal info
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    birthdate = serializers.DateField(required=False, allow_null=True)
    height_cm = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    weight_kg = serializers.FloatField(required=False, allow_null=True, min_value=0)
    address = serializers.CharField(required=False, allow_blank=True)
    injury_notes = serializers.CharField(required=False, allow_blank=True, max_length=1_000)

    # Cycling
    seat_height = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    seat_distance = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    handlebar_distance = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    cycling_shoe_size = serializers.FloatField(required=False, allow_null=True, min_value=0)
    waitlist_auto_confirm = serializers.BooleanField(required=False)


class FavoritesSerializer(serializers.Serializer):
    instructor_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    time_slots = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    spots = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate_time_slots(self, value):
        validated = []
        for item in value:
            allowed = {"weekday", "start_hour", "end_hour"}
            if set(item) != allowed:
                raise serializers.ValidationError(
                    "Cada bloque requiere weekday, start_hour y end_hour."
                )
            try:
                weekday, start, end = (
                    int(item["weekday"]),
                    int(item["start_hour"]),
                    int(item["end_hour"]),
                )
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError("Los bloques de hora deben ser enteros.") from exc
            if not 0 <= weekday <= 6 or not 0 <= start <= 23 or not 1 <= end <= 24 or start >= end:
                raise serializers.ValidationError("Bloque horario inválido.")
            validated.append({"weekday": weekday, "start_hour": start, "end_hour": end})
        return validated

    def validate_spots(self, value):
        validated = []
        for item in value:
            if set(item) != {"room_id", "spot"}:
                raise serializers.ValidationError("Cada spot requiere room_id y spot.")
            try:
                spot = int(item["spot"])
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError("spot debe ser un entero positivo.") from exc
            if spot < 1:
                raise serializers.ValidationError("spot debe ser positivo.")
            try:
                room_id = UUID(str(item["room_id"]))
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError("room_id debe ser un UUID.") from exc
            validated.append({"room_id": room_id, "spot": spot})
        return validated


class AlertPreferenceSerializer(serializers.Serializer):
    email_enabled = serializers.BooleanField(required=False, default=True)
    quiet_hours_start = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=23
    )
    quiet_hours_end = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=23
    )

    def validate(self, attrs):
        start, end = attrs.get("quiet_hours_start"), attrs.get("quiet_hours_end")
        if (start is None) != (end is None):
            raise serializers.ValidationError(
                "quiet_hours_start y quiet_hours_end deben enviarse juntos."
            )
        return attrs
