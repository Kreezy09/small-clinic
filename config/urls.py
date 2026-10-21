"""Root URL routes of the clinic booking API."""

from django.urls import path

from appointments.views import (
    AppointmentCancelView,
    AppointmentCreateView,
    AppointmentRescheduleView,
)
from doctors.views import DoctorAvailabilityView

urlpatterns = [
    path("appointments", AppointmentCreateView.as_view(), name="appointment-create"),
    path(
        "appointments/<int:pk>/cancel",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
    path(
        "appointments/<int:pk>/reschedule",
        AppointmentRescheduleView.as_view(),
        name="appointment-reschedule",
    ),
    path(
        "doctors/<int:pk>/availability",
        DoctorAvailabilityView.as_view(),
        name="doctor-availability",
    ),
]
