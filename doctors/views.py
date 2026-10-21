"""HTTP endpoints for doctors."""

from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from appointments.models import Appointment
from doctors.models import Doctor
from doctors.serializers import AvailabilityQuerySerializer, AvailabilitySerializer


class DoctorAvailabilityView(generics.GenericAPIView):
    """``GET /doctors/{id}/availability?date=YYYY-MM-DD``: list bookable slots."""

    queryset = Doctor.objects.all()

    def get(self, request: Request, pk: int) -> Response:
        """Return the doctor's bookable slots on the requested clinic-local date."""
        doctor = self.get_object()
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data["date"]
        availability = {
            "doctor_id": doctor.pk,
            "date": day,
            "slots": Appointment.available_slots(doctor, day),
        }
        return Response(AvailabilitySerializer(availability).data)
