"""Request and response serializers for patients."""

from rest_framework import serializers

from patients.models import Patient


class PatientSerializer(serializers.Serializer):
    """Registers a patient and represents it in responses."""

    id = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.EmailField(source="user.email")
    first_name = serializers.CharField(source="user.first_name", max_length=150)
    last_name = serializers.CharField(source="user.last_name", max_length=150)
    phone = serializers.CharField(
        source="user.phone", max_length=20, allow_null=True, default=None
    )

    def create(self, validated_data: dict[str, dict[str, str | None]]) -> Patient:
        """Register the patient described by the validated request."""
        user = validated_data["user"]
        return Patient.register(
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone=user["phone"],
        )
