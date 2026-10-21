"""Root URL routes of the clinic booking API."""

from django.urls import path

from appointments.views import AppointmentCreateView
from doctors.views import DoctorAvailabilityView

urlpatterns = [
    path("appointments", AppointmentCreateView.as_view(), name="appointment-create"),
    path(
        "doctors/<int:pk>/availability",
        DoctorAvailabilityView.as_view(),
        name="doctor-availability",
    ),
]
