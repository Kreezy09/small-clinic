"""Domain errors raised by appointment operations."""


class AppointmentError(Exception):
    """Base class for appointment rule violations."""


class SlotNotBookableError(AppointmentError):
    """The requested time breaks a booking rule."""


class SlotUnavailableError(AppointmentError):
    """The requested time overlaps another active appointment."""
