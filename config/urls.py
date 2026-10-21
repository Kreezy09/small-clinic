"""Root URL routes of the clinic booking API."""

from django.urls import path

from appointments.views import AppointmentCreateView

urlpatterns = [
    path("appointments", AppointmentCreateView.as_view(), name="appointment-create"),
]
