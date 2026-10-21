"""Appointment API endpoints."""

from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from appointments.models import Appointment
from appointments.serializers import (
    AppointmentSerializer,
    CancelAppointmentSerializer,
    RescheduleAppointmentSerializer,
)


class AppointmentViewSet(CreateModelMixin, GenericViewSet):
    """Book, cancel and reschedule appointments."""

    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    lookup_value_regex = r"\d+"

    @action(
        detail=True, methods=["patch"], serializer_class=CancelAppointmentSerializer
    )
    def cancel(self, request: Request, pk: str) -> Response:
        """Cancel the appointment with an optional reason and return it."""
        appointment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment.cancel(serializer.validated_data["reason"])
        return Response(AppointmentSerializer(appointment).data)

    @action(
        detail=True,
        methods=["patch"],
        serializer_class=RescheduleAppointmentSerializer,
    )
    def reschedule(self, request: Request, pk: str) -> Response:
        """Move the appointment to a new slot and return it."""
        appointment = self.get_object()
        serializer = self.get_serializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment.reschedule(
            start_at=serializer.validated_data["start_at"],
            doctor=serializer.validated_data["doctor"],
        )
        return Response(AppointmentSerializer(appointment).data)
