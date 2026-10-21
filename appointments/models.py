"""Appointments between a doctor and a patient, and the rules for booking them."""

from datetime import date, datetime, time, timedelta
from typing import Self

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import IntegrityError, connection, models, transaction
from django.db.models import Func
from django.utils import timezone
from psycopg.errors import ExclusionViolation

from appointments.exceptions import (
    AppointmentStateError,
    SlotNotBookableError,
    SlotUnavailableError,
)
from core.models import TimestampedModel
from doctors.models import Doctor, Slot
from patients.models import Patient

DOCTOR_OVERLAP_CONSTRAINT = "appointments_no_doctor_overlap"
PATIENT_OVERLAP_CONSTRAINT = "appointments_no_patient_overlap"
DOCTOR_BUSY_MESSAGE = "The doctor already has an appointment in this slot."
PATIENT_BUSY_MESSAGE = "The patient already has an appointment at this time."
OVERLAP_MESSAGES = {
    DOCTOR_OVERLAP_CONSTRAINT: DOCTOR_BUSY_MESSAGE,
    PATIENT_OVERLAP_CONSTRAINT: PATIENT_BUSY_MESSAGE,
}


class TsTzRange(Func):
    """PostgreSQL ``tstzrange(start, end)``, half-open by default."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class AppointmentStatus(models.TextChoices):
    """Lifecycle states of an appointment."""

    BOOKED = "BOOKED", "Booked"
    CANCELLED = "CANCELLED", "Cancelled"


HOLDS_SLOT = ~models.Q(status=AppointmentStatus.CANCELLED)


class AppointmentQuerySet(models.QuerySet["Appointment"]):
    """Query helpers for appointments."""

    def active(self) -> Self:
        """Return appointments that still hold their slot."""
        return self.filter(HOLDS_SLOT)

    def overlapping(self, start_at: datetime, end_at: datetime) -> Self:
        """Return appointments whose time range overlaps ``[start_at, end_at)``."""
        return self.filter(start_at__lt=end_at, end_at__gt=start_at)

    def upcoming(self) -> Self:
        """Return active appointments starting now or later, earliest first."""
        return self.active().filter(start_at__gte=timezone.now()).order_by("start_at")


class Appointment(TimestampedModel):
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

    @classmethod
    def available_slots(cls, doctor: Doctor, day: date) -> list[Slot]:
        """Return the doctor's slots on a clinic-local date that can be booked now.

        Args:
            doctor: Doctor whose slots to list.
            day: Date in the clinic time zone.

        Returns:
            Slots in start order that start no earlier than the minimum booking
            lead time and overlap no active appointment of the doctor; empty when
            the doctor is not accepting appointments.
        """
        if not doctor.accepting_appointments:
            return []
        day_start = datetime.combine(day, time.min, tzinfo=settings.CLINIC_TIMEZONE)
        booked = list(
            doctor.appointments.active()
            .overlapping(day_start, day_start + timedelta(days=1))
            .values_list("start_at", "end_at")
        )
        earliest = earliest_bookable_start()
        return [
            slot
            for slot in doctor.slots_on(day)
            if slot.start >= earliest and not slot.overlaps_any(booked)
        ]

    @classmethod
    def book(
        cls, doctor: Doctor, patient: Patient, start_at: datetime, reason: str | None
    ) -> "Appointment":
        """Book the doctor's slot starting at ``start_at`` for the patient.

        Args:
            doctor: Doctor to see.
            patient: Patient booking the slot.
            start_at: Timezone-aware start of the slot.
            reason: Patient's reason for the visit.

        Returns:
            The saved appointment.

        Raises:
            SlotNotBookableError: The time is not a bookable slot of the doctor.
            SlotUnavailableError: The slot overlaps an active appointment of the
                doctor or the patient.
        """
        appointment = cls(doctor=doctor, patient=patient, reason=reason)
        with transaction.atomic():
            appointment.lock_slot_owners()
            appointment.assign_slot(start_at)
            appointment.save_slot()
        return appointment

    def cancel(self, reason: str | None) -> None:
        """Cancel the appointment, freeing its slot.

        Args:
            reason: Why the appointment was cancelled.

        Raises:
            AppointmentStateError: The appointment is already cancelled.
        """
        now = timezone.now()
        cancelled = (
            Appointment.objects.active()
            .filter(pk=self.pk)
            .update(
                status=AppointmentStatus.CANCELLED,
                cancellation_reason=reason,
                cancelled_at=now,
                updated_at=now,
            )
        )
        if not cancelled:
            raise AppointmentStateError("The appointment is already cancelled.")
        self.refresh_from_db()

    def reschedule(self, start_at: datetime, doctor: Doctor) -> None:
        """Move the appointment to the doctor's slot starting at ``start_at``.

        The previous slot is freed. The new slot is validated as for a new booking.

        Args:
            start_at: Timezone-aware start of the new slot.
            doctor: Doctor of the new slot; may differ from the current doctor.

        Raises:
            AppointmentStateError: The appointment is cancelled.
            SlotNotBookableError: The time is not a bookable slot of the doctor.
            SlotUnavailableError: The slot overlaps another active appointment of
                the doctor or the patient.
        """
        with transaction.atomic():
            current = Appointment.objects.select_for_update().get(pk=self.pk)
            if current.status == AppointmentStatus.CANCELLED:
                raise AppointmentStateError(
                    "Cancelled appointments cannot be rescheduled."
                )
            self.doctor = doctor
            self.lock_slot_owners()
            self.assign_slot(start_at)
            self.save_slot(update_fields=("doctor", "start_at", "end_at", "updated_at"))

    def lock_slot_owners(self) -> None:
        """Lock the appointment's doctor, then its patient, until the transaction ends.

        Concurrent bookings and reschedules that share the doctor or the patient
        wait for each other, so each sees the others' committed appointments.
        """
        with connection.cursor() as cursor:
            for key in (f"doctor:{self.doctor_id}", f"patient:{self.patient_id}"):
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [key]
                )

    def assign_slot(self, start_at: datetime) -> None:
        """Validate the doctor's slot starting at ``start_at`` and take its times.

        Args:
            start_at: Timezone-aware start of the slot.

        Raises:
            SlotNotBookableError: The time is not a bookable slot of the doctor.
            SlotUnavailableError: The slot overlaps an active appointment of the
                doctor or the patient.
        """
        if not self.doctor.accepting_appointments:
            raise SlotNotBookableError("The doctor is not accepting appointments.")
        ensure_bookable_start(start_at)
        slot = self.doctor.slot_starting_at(start_at)
        if slot is None:
            raise SlotNotBookableError(
                "The requested time is not a slot within the doctor's working hours."
            )
        self.start_at, self.end_at = slot.start, slot.end
        self.ensure_no_overlap()

    def ensure_no_overlap(self) -> None:
        """Raise if the assigned slot overlaps another active appointment.

        Raises:
            SlotUnavailableError: The doctor or the patient is already booked.
        """
        clashes = (
            Appointment.objects.active()
            .overlapping(self.start_at, self.end_at)
            .exclude(pk=self.pk)
        )
        if clashes.filter(doctor=self.doctor).exists():
            raise SlotUnavailableError(DOCTOR_BUSY_MESSAGE)
        if clashes.filter(patient=self.patient).exists():
            raise SlotUnavailableError(PATIENT_BUSY_MESSAGE)

    def save_slot(self, update_fields: tuple[str, ...] | None = None) -> None:
        """Save the appointment, reporting a concurrent overlap as a domain error.

        Args:
            update_fields: Fields to write, or ``None`` to write every field.

        Raises:
            SlotUnavailableError: An overlap constraint rejected the slot.
        """
        try:
            with transaction.atomic():
                self.save(update_fields=update_fields)
        except IntegrityError as exc:
            if not isinstance(exc.__cause__, ExclusionViolation):
                raise
            raise SlotUnavailableError(
                OVERLAP_MESSAGES[exc.__cause__.diag.constraint_name]
            ) from exc


def ensure_bookable_start(start_at: datetime) -> None:
    """Raise if ``start_at`` is in the past or inside the minimum booking lead time.

    Args:
        start_at: Timezone-aware start of the slot.

    Raises:
        SlotNotBookableError: The start is too early to book.
    """
    if start_at < timezone.now():
        raise SlotNotBookableError("Appointments cannot be booked in the past.")
    if start_at < earliest_bookable_start():
        raise SlotNotBookableError(
            "Appointments must be booked at least "
            f"{settings.BOOKING_MIN_LEAD_TIME // timedelta(minutes=1)} minutes ahead."
        )


def earliest_bookable_start() -> datetime:
    """Return the earliest start time that can be booked now."""
    return timezone.now() + settings.BOOKING_MIN_LEAD_TIME
