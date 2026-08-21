from rest_framework import serializers


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

    # Cycling
    seat_height = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    seat_distance = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    handlebar_distance = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    cycling_shoe_size = serializers.FloatField(required=False, allow_null=True, min_value=0)
    waitlist_auto_confirm = serializers.BooleanField(required=False)
