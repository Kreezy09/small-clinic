"""Domain errors raised by appointment operations."""

from core.exceptions import DomainError


class AppointmentError(DomainError):
    """Base class for appointment rule violations."""


class SlotNotBookableError(AppointmentError):
    """The requested time breaks a booking rule."""


class SlotUnavailableError(AppointmentError):
    """The requested time overlaps another active appointment."""


class AppointmentStateError(AppointmentError):
    """The appointment's status does not allow the requested change."""
