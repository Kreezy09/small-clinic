"""Appointments between a doctor and a patient."""

from datetime import datetime
from typing import Self

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import Func
from django.utils import timezone

from appointments.mixins.booking import (
    DOCTOR_OVERLAP_CONSTRAINT,
    PATIENT_OVERLAP_CONSTRAINT,
    AppointmentBookingMixin,
)
from appointments.mixins.lifecycle import AppointmentLifecycleMixin
from core.models import TimestampedModel
from doctors.models import Doctor
from patients.models import Patient


class TsTzRange(Func):
    """PostgreSQL ``tstzrange(start, end)``, half-open by default."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class AppointmentStatus(models.TextChoices):
    """Lifecycle states of an appointment."""

    BOOKED = "BOOKED", "Booked"
    CANCELLED = "CANCELLED", "Cancelled"


HOLDS_SLOT = ~models.Q(status=AppointmentStatus.CANCELLED)


class AppointmentQuerySet(models.QuerySet):
    """Filters and bulk changes for appointments."""

    def active(self) -> Self:
        """Return appointments that still hold their slot."""
        return self.filter(HOLDS_SLOT)

    def overlapping(self, start_at: datetime, end_at: datetime) -> Self:
        """Return appointments whose time range overlaps ``[start_at, end_at)``."""
        return self.filter(start_at__lt=end_at, end_at__gt=start_at)

    def upcoming(self) -> Self:
        """Return active appointments starting now or later, earliest first."""
        return self.active().filter(start_at__gte=timezone.now()).order_by("start_at")

    def cancel(self, reason: str | None) -> int:
        """Cancel the active appointments in this queryset.

        Args:
            reason: Why the appointments were cancelled.

        Returns:
            The number of appointments cancelled.
        """
        now = timezone.now()
        return self.active().update(
            status=AppointmentStatus.CANCELLED,
            cancellation_reason=reason,
            cancelled_at=now,
            updated_at=now,
        )


class Appointment(AppointmentBookingMixin, AppointmentLifecycleMixin, TimestampedModel):
    """A patient's booking of one of a doctor's slots."""

    doctor = models.ForeignKey(
        Doctor, on_delete=models.PROTECT, related_name="appointments"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.PROTECT, related_name="appointments"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.BOOKED,
    )
    reason = models.TextField(null=True, blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    objects = AppointmentQuerySet.as_manager()

    class Meta:
        constraints = (
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="appointments_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=AppointmentStatus.values),
                name="appointments_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status=AppointmentStatus.CANCELLED, cancelled_at__isnull=False
                )
                | (
                    ~models.Q(status=AppointmentStatus.CANCELLED)
                    & models.Q(cancelled_at__isnull=True)
                ),
                name="appointments_cancelled_at_matches_status",
            ),
            ExclusionConstraint(
                name=DOCTOR_OVERLAP_CONSTRAINT,
                expressions=[
                    ("doctor", RangeOperators.EQUAL),
                    (TsTzRange("start_at", "end_at"), RangeOperators.OVERLAPS),
                ],
                condition=HOLDS_SLOT,
            ),
            ExclusionConstraint(
                name=PATIENT_OVERLAP_CONSTRAINT,
                expressions=[
                    ("patient", RangeOperators.EQUAL),
                    (TsTzRange("start_at", "end_at"), RangeOperators.OVERLAPS),
                ],
                condition=HOLDS_SLOT,
            ),
        )
        indexes = (
            models.Index(
                fields=["patient", "start_at"], name="appointments_patient_start"
            ),
        )

    def __str__(self) -> str:
        return f"{self.patient} with {self.doctor} at {self.start_at:%Y-%m-%d %H:%M}"
