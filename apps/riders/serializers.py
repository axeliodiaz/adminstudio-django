from rest_framework import serializers


class RiderSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    created = serializers.DateTimeField(read_only=True)
