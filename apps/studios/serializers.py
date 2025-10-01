"""Serializers for studios app (manual fields, no ModelSerializer)."""

from rest_framework import serializers


class StudioSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    address = serializers.CharField(max_length=255)
    is_active = serializers.BooleanField(required=False, default=False)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)


class RoomSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    studio = serializers.UUIDField(source="studio_id", read_only=True)
    name = serializers.CharField(max_length=100)
    capacity = serializers.IntegerField(min_value=0)
    is_active = serializers.BooleanField(required=False, default=False)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
