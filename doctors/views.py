"""Doctor API endpoints."""

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from doctors.models import Doctor
from doctors.serializers import AvailabilityQuerySerializer, AvailabilitySerializer


class DoctorViewSet(GenericViewSet):
    """Doctor scheduling endpoints."""

    queryset = Doctor.objects.all()
    lookup_value_regex = r"\d+"

    @action(detail=True, methods=["get"])
    def availability(self, request: Request, pk: str) -> Response:
        """Return the doctor's bookable slots on the requested clinic-local date."""
        doctor = self.get_object()
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data["date"]
        availability = {
            "doctor_id": doctor.pk,
            "date": day,
            "slots": doctor.available_slots(day),
        }
        return Response(AvailabilitySerializer(availability).data)
