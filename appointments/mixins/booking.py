"""Booking an appointment into a free slot of a doctor."""

from datetime import datetime
from typing import Self

from django.db import IntegrityError, connection, transaction
from psycopg.errors import ExclusionViolation

from appointments.exceptions import SlotUnavailableError
from doctors.models import Doctor
from patients.models import Patient

DOCTOR_OVERLAP_CONSTRAINT = "appointments_no_doctor_overlap"
PATIENT_OVERLAP_CONSTRAINT = "appointments_no_patient_overlap"
DOCTOR_BUSY_MESSAGE = "The doctor already has an appointment in this slot."
PATIENT_BUSY_MESSAGE = "The patient already has an appointment at this time."
OVERLAP_MESSAGES = {
    DOCTOR_OVERLAP_CONSTRAINT: DOCTOR_BUSY_MESSAGE,
    PATIENT_OVERLAP_CONSTRAINT: PATIENT_BUSY_MESSAGE,
}


class AppointmentBookingMixin:
    """Validates, locks and saves an appointment's slot."""

    @classmethod
    def book(
        cls, doctor: Doctor, patient: Patient, start_at: datetime, reason: str | None
    ) -> Self:
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
        slot = self.doctor.bookable_slot(start_at)
        self.start_at, self.end_at = slot.start, slot.end
        self.ensure_no_overlap()

    def ensure_no_overlap(self) -> None:
        """Raise if the assigned slot overlaps another active appointment.

        Raises:
            SlotUnavailableError: The doctor or the patient is already booked.
        """
        clashes = (
            type(self)
            .objects.active()
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
