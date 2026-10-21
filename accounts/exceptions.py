"""Domain errors raised by user accounts."""

from core.exceptions import DomainError


class EmailTakenError(DomainError):
    """Another user already has the email."""
