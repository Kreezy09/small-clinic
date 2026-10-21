"""Root URL routes of the clinic booking API."""

from django.urls import path

from appointments.views import AppointmentCancelView, AppointmentCreateView
from doctors.views import DoctorAvailabilityView

urlpatterns = [
    path("appointments", AppointmentCreateView.as_view(), name="appointment-create"),
    path(
        "appointments/<int:pk>/cancel",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
    path(
        "doctors/<int:pk>/availability",
        DoctorAvailabilityView.as_view(),
        name="doctor-availability",
    ),
]
