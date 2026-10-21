"""Cancelling and rescheduling an appointment."""

from datetime import datetime

from django.db import transaction

from appointments.exceptions import AppointmentStateError
from doctors.models import Doctor


class AppointmentLifecycleMixin:
    """Moves an appointment between slots and statuses."""

    def cancel(self, reason: str | None) -> None:
        """Cancel the appointment, freeing its slot.

        Args:
            reason: Why the appointment was cancelled.

        Raises:
            AppointmentStateError: The appointment is already cancelled.
        """
        if not type(self).objects.filter(pk=self.pk).cancel(reason):
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
            active = type(self).objects.active().select_for_update()
            if active.filter(pk=self.pk).first() is None:
                raise AppointmentStateError(
                    "Cancelled appointments cannot be rescheduled."
                )
            self.doctor = doctor
            self.lock_slot_owners()
            self.assign_slot(start_at)
            self.save_slot(update_fields=("doctor", "start_at", "end_at", "updated_at"))
