"""Request and response serializers for appointments."""

from rest_framework import serializers

from appointments.models import Appointment
from doctors.models import Doctor
from patients.models import Patient


class CurrentDoctorDefault:
    """Field default that resolves to the doctor of the serializer's appointment."""

    requires_context = True

    def __call__(self, serializer_field: serializers.Field) -> Doctor:
        return serializer_field.parent.instance.doctor


class AppointmentSerializer(serializers.ModelSerializer):
    """Books an appointment and represents it in responses."""

    doctor_id = serializers.PrimaryKeyRelatedField(
        source="doctor", queryset=Doctor.objects.all()
    )
    patient_id = serializers.PrimaryKeyRelatedField(
        source="patient", queryset=Patient.objects.all()
    )
    reason = serializers.CharField(allow_null=True, default=None)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "doctor_id",
            "patient_id",
            "start_at",
            "end_at",
            "status",
            "reason",
            "cancellation_reason",
            "cancelled_at",
        )
        read_only_fields = (
            "end_at",
            "status",
            "cancellation_reason",
            "cancelled_at",
        )
        validators = ()

    def create(self, validated_data: dict[str, object]) -> Appointment:
        """Book the appointment described by the validated request."""
        return Appointment.book(
            doctor=validated_data["doctor"],
            patient=validated_data["patient"],
            start_at=validated_data["start_at"],
            reason=validated_data["reason"],
        )


class CancelAppointmentSerializer(serializers.Serializer):
    """Request body of the cancel endpoint."""

    reason = serializers.CharField(allow_null=True, default=None)


class RescheduleAppointmentSerializer(serializers.Serializer):
    """Request body of the reschedule endpoint, bound to the appointment."""

    doctor_id = serializers.PrimaryKeyRelatedField(
        source="doctor", queryset=Doctor.objects.all(), default=CurrentDoctorDefault()
    )
    start_at = serializers.DateTimeField()
