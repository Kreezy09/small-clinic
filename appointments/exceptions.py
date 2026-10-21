"""Domain errors raised by appointment operations."""

from core.exceptions import DomainError


class SlotUnavailableError(DomainError):
    """The requested time overlaps another active appointment."""


class AppointmentStateError(DomainError):
    """The appointment's status does not allow the requested change."""
