"""Domain errors raised by patient operations."""

from core.exceptions import DomainError


class EmailTakenError(DomainError):
    """Another user already has the email."""
