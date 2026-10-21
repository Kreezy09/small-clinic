"""DRF exception handler that maps domain errors to HTTP responses."""

from collections.abc import Mapping

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from accounts.exceptions import EmailTakenError
from appointments.exceptions import AppointmentStateError, SlotUnavailableError
from core.exceptions import DomainError
from doctors.exceptions import SlotNotBookableError

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    SlotNotBookableError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SlotUnavailableError: status.HTTP_409_CONFLICT,
    AppointmentStateError: status.HTTP_409_CONFLICT,
    EmailTakenError: status.HTTP_409_CONFLICT,
}


def handle_exception(exc: Exception, context: Mapping[str, object]) -> Response | None:
    """Return the HTTP response for an exception raised by a view.

    Args:
        exc: Exception raised while handling the request.
        context: View context supplied by DRF.

    Returns:
        A response for domain errors and DRF exceptions, or ``None`` to let
        other exceptions propagate.
    """
    if isinstance(exc, DomainError):
        return Response({"detail": str(exc)}, status=STATUS_BY_ERROR[type(exc)])
    return exception_handler(exc, context)
