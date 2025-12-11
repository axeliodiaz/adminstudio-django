"""Serializers for studios app (manual fields, no ModelSerializer)."""

from rest_framework import serializers


class StudioSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    address = serializers.CharField(max_length=255, required=False, allow_null=True)
    address_id = serializers.UUIDField(read_only=True, required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=False)
    opening_time = serializers.TimeField(required=False, allow_null=True)
    closing_time = serializers.TimeField(required=False, allow_null=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        """Override to handle address ForeignKey."""
        ret = super().to_representation(instance)
        # Handle address ForeignKey - check if it's an Address instance or already a string
        if instance.address:
            if hasattr(instance.address, "address"):
                # It's an Address instance
                ret["address"] = instance.address.address
                ret["address_id"] = str(instance.address.id)
            else:
                # It's already a string (backward compatibility)
                ret["address"] = str(instance.address)
                ret["address_id"] = None
        else:
            ret["address"] = None
            ret["address_id"] = None
        return ret


class RoomSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    studio = serializers.UUIDField(source="studio_id", read_only=True)
    name = serializers.CharField(max_length=100)
    capacity = serializers.IntegerField(min_value=0)
    is_active = serializers.BooleanField(required=False, default=False)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
