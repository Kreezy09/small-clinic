"""Domain errors raised by doctor scheduling."""

from core.exceptions import DomainError


class SlotNotBookableError(DomainError):
    """The requested time is not a bookable slot of the doctor."""
