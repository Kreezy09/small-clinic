"""Patient API endpoints."""

from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from appointments.serializers import AppointmentSerializer
from patients.models import Patient
from patients.serializers import PatientSerializer


class PatientViewSet(CreateModelMixin, GenericViewSet):
    """Register patients and list their upcoming appointments."""

    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    lookup_value_regex = r"\d+"

    @action(detail=True, methods=["get"])
    def appointments(self, request: Request, pk: str) -> Response:
        """Return the patient's upcoming appointments, earliest first."""
        patient = self.get_object()
        upcoming = patient.appointments.upcoming()
        return Response(AppointmentSerializer(upcoming, many=True).data)
