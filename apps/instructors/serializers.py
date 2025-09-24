from rest_framework import serializers


class InstructorSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    birthdate = serializers.DateField()
    address = serializers.CharField()
