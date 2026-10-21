"""HTTP endpoints for appointments."""

from rest_framework import generics

from appointments.serializers import AppointmentSerializer


class AppointmentCreateView(generics.CreateAPIView):
    """``POST /appointments``: book a doctor's slot for a patient."""

    serializer_class = AppointmentSerializer
