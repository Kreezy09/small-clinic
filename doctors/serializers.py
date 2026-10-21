"""Request and response serializers for doctor endpoints."""

from rest_framework import serializers


class AvailabilityQuerySerializer(serializers.Serializer):
    """Query parameters of the availability endpoint."""

    date = serializers.DateField()


class SlotSerializer(serializers.Serializer):
    """A bookable slot."""

    start_at = serializers.DateTimeField(source="start")
    end_at = serializers.DateTimeField(source="end")


class AvailabilitySerializer(serializers.Serializer):
    """A doctor's bookable slots on one date."""

    doctor_id = serializers.IntegerField()
    date = serializers.DateField()
    slots = SlotSerializer(many=True)
