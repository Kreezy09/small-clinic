"""HTTP endpoints for appointments."""

from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer, CancelAppointmentSerializer


class AppointmentCreateView(generics.CreateAPIView):
    """``POST /appointments``: book a doctor's slot for a patient."""

    serializer_class = AppointmentSerializer


class AppointmentCancelView(generics.GenericAPIView):
    """``PATCH /appointments/{id}/cancel``: cancel an appointment with a reason."""

    queryset = Appointment.objects.all()
    serializer_class = CancelAppointmentSerializer

    def patch(self, request: Request, pk: int) -> Response:
        """Cancel the appointment and return it."""
        appointment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment.cancel(serializer.validated_data["reason"])
        return Response(AppointmentSerializer(appointment).data)
