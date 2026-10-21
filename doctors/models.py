"""Doctors, their weekly working hours, and the bookable slots derived from them."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import pairwise

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimestampedModel


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

    def slot_starting_at(self, start_at: datetime) -> Slot | None:
        """Return the working-hours slot that starts exactly at ``start_at``.

        Args:
            start_at: Timezone-aware start time.

        Returns:
            The matching slot, or ``None`` when no slot starts at that time.
        """
        day = start_at.astimezone(settings.CLINIC_TIMEZONE).date()
        return next(
            (slot for slot in self.slots_on(day) if slot.start == start_at), None
        )


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
