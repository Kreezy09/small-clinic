"""Doctors, their weekly working hours, and the bookable slots derived from them."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import pairwise

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimestampedModel
from doctors.exceptions import SlotNotBookableError


class Weekday(models.IntegerChoices):
    """ISO weekday numbers, matching ``date.isoweekday()``."""

    MONDAY = 1, "Monday"
    TUESDAY = 2, "Tuesday"
    WEDNESDAY = 3, "Wednesday"
    THURSDAY = 4, "Thursday"
    FRIDAY = 5, "Friday"
    SATURDAY = 6, "Saturday"
    SUNDAY = 7, "Sunday"


@dataclass(frozen=True)
class Slot:
    """A bookable time range, start inclusive and end exclusive."""

    start: datetime
    end: datetime

    def overlaps_any(self, ranges: list[tuple[datetime, datetime]]) -> bool:
        """Return whether the slot overlaps any half-open ``(start, end)`` range."""
        return any(start < self.end and self.start < end for start, end in ranges)


class Doctor(TimestampedModel):
    """Doctor profile of a user, holding the doctor's booking settings."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        primary_key=True,
        related_name="doctor",
    )
    slot_minutes = models.PositiveSmallIntegerField(default=30)
    accepting_appointments = models.BooleanField(default=True)

    class Meta:
        constraints = (
            models.CheckConstraint(
                condition=models.Q(slot_minutes__gt=0),
                name="doctors_slot_minutes_positive",
            ),
        )

    def __str__(self) -> str:
        return str(self.user)

    def slots_on(self, day: date) -> list[Slot]:
        """Return every slot of the doctor's working hours on a clinic-local date.

        Args:
            day: Date in the clinic time zone.

        Returns:
            Slots in start order, regardless of existing appointments.
        """
        length = timedelta(minutes=self.slot_minutes)
        blocks = self.working_hours.filter(
            iso_weekday=Weekday(day.isoweekday())
        ).order_by("start_time")
        return [slot for block in blocks for slot in block.slots_on(day, length)]

    def available_slots(self, day: date) -> list[Slot]:
        """Return the doctor's slots on a clinic-local date that can be booked now.

        Args:
            day: Date in the clinic time zone.

        Returns:
            Slots in start order that start no earlier than the minimum booking
            lead time and overlap no active appointment of the doctor; empty when
            the doctor is not accepting appointments.
        """
        if not self.accepting_appointments:
            return []
        day_start = datetime.combine(day, time.min, tzinfo=settings.CLINIC_TIMEZONE)
        booked = list(
            self.appointments.active()
            .overlapping(day_start, day_start + timedelta(days=1))
            .values_list("start_at", "end_at")
        )
        earliest = self.earliest_bookable_start()
        return [
            slot
            for slot in self.slots_on(day)
            if slot.start >= earliest and not slot.overlaps_any(booked)
        ]

    def bookable_slot(self, start_at: datetime) -> Slot:
        """Return the slot starting at ``start_at`` if the doctor can be booked then.

        Args:
            start_at: Timezone-aware start of the slot.

        Returns:
            The working-hours slot starting at ``start_at``.

        Raises:
            SlotNotBookableError: The doctor is not accepting appointments, the
                start is in the past or inside the lead time, or no slot starts
                at that time.
        """
        if not self.accepting_appointments:
            raise SlotNotBookableError("The doctor is not accepting appointments.")
        if start_at < timezone.now():
            raise SlotNotBookableError("Appointments cannot be booked in the past.")
        if start_at < self.earliest_bookable_start():
            raise SlotNotBookableError(
                "Appointments must be booked at least "
                f"{settings.BOOKING_MIN_LEAD_TIME // timedelta(minutes=1)} "
                "minutes ahead."
            )
        day = start_at.astimezone(settings.CLINIC_TIMEZONE).date()
        slot = next((s for s in self.slots_on(day) if s.start == start_at), None)
        if slot is None:
            raise SlotNotBookableError(
                "The requested time is not a slot within the doctor's working hours."
            )
        return slot

    @staticmethod
    def earliest_bookable_start() -> datetime:
        """Return the earliest start time that can be booked now."""
        return timezone.now() + settings.BOOKING_MIN_LEAD_TIME


class DoctorWorkingHours(TimestampedModel):
    """One continuous block of a doctor's recurring weekly hours, in clinic time."""

    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="working_hours"
    )
    iso_weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["doctor", "iso_weekday", "start_time"],
                name="doctor_working_hours_unique_start",
            ),
            models.CheckConstraint(
                condition=models.Q(iso_weekday__gte=1, iso_weekday__lte=7),
                name="doctor_working_hours_iso_weekday_range",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="doctor_working_hours_end_after_start",
            ),
        )

    @staticmethod
    def ensure_no_overlap(blocks: Iterable["DoctorWorkingHours"]) -> None:
        """Raise if any two blocks of one doctor overlap on the same weekday.

        Args:
            blocks: Every working-hours block of one doctor.

        Raises:
            ValidationError: Two blocks share a weekday and overlap in time.
        """
        ordered = sorted(
            blocks, key=lambda block: (block.iso_weekday, block.start_time)
        )
        for earlier, later in pairwise(ordered):
            if (
                earlier.iso_weekday == later.iso_weekday
                and later.start_time < earlier.end_time
            ):
                raise ValidationError(
                    f"Working hours overlap on {Weekday(later.iso_weekday).label}: "
                    f"{earlier.start_time:%H:%M}-{earlier.end_time:%H:%M} and "
                    f"{later.start_time:%H:%M}-{later.end_time:%H:%M}."
                )

    def slots_on(self, day: date, length: timedelta) -> list[Slot]:
        """Split this block into consecutive slots on a date.

        Args:
            day: Date in the clinic time zone.
            length: Length of each slot.

        Returns:
            Slots from the block start that end by the block end.
        """
        start = datetime.combine(day, self.start_time, tzinfo=settings.CLINIC_TIMEZONE)
        end = datetime.combine(day, self.end_time, tzinfo=settings.CLINIC_TIMEZONE)
        return [
            Slot(start + index * length, start + (index + 1) * length)
            for index in range((end - start) // length)
        ]
