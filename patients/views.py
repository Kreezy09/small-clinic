"""HTTP endpoints for patients."""

from django.shortcuts import get_object_or_404
from rest_framework import generics

from appointments.models import AppointmentQuerySet
from appointments.serializers import AppointmentSerializer
from patients.models import Patient


class PatientAppointmentListView(generics.ListAPIView):
    """``GET /patients/{id}/appointments``: the patient's upcoming appointments."""

    serializer_class = AppointmentSerializer

    def get_queryset(self) -> AppointmentQuerySet:
        """Return the patient's upcoming appointments, earliest first."""
        patient = get_object_or_404(Patient, pk=self.kwargs["pk"])
        return patient.appointments.upcoming()
