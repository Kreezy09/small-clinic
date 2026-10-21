"""Shared test data builders and API request helpers."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from doctors.models import Doctor, Weekday
from patients.models import Patient

NAIROBI = ZoneInfo("Africa/Nairobi")
NOW = datetime(2026, 10, 26, 7, 0, tzinfo=NAIROBI)


def create_doctor(email: str, first_name: str) -> Doctor:
    """Create a doctor working Mondays 08:00-10:15 and 10:30-13:00."""
    user = get_user_model().objects.create_user(
        email=email, first_name=first_name, last_name="Testdoctor"
    )
    doctor = Doctor.objects.create(user=user)
    doctor.working_hours.create(
        iso_weekday=Weekday.MONDAY, start_time=time(8, 0), end_time=time(10, 15)
    )
    doctor.working_hours.create(
        iso_weekday=Weekday.MONDAY, start_time=time(10, 30), end_time=time(13, 0)
    )
    return doctor


def create_patient(email: str, first_name: str) -> Patient:
    """Create a patient and its user."""
    user = get_user_model().objects.create_user(
        email=email, first_name=first_name, last_name="Testpatient"
    )
    return Patient.objects.create(user=user)


def book(
    api_client: APIClient, doctor: Doctor, patient: Patient, start_at: str, **extra
):
    """Send ``POST /appointments`` for the doctor and patient."""
    payload = {
        "doctor_id": doctor.pk,
        "patient_id": patient.pk,
        "start_at": start_at,
        **extra,
    }
    return api_client.post("/appointments", payload, format="json")


def cancel(api_client: APIClient, appointment_id: int, **body):
    """Send ``PATCH /appointments/{id}/cancel``."""
    return api_client.patch(
        f"/appointments/{appointment_id}/cancel", body, format="json"
    )


def reschedule(api_client: APIClient, appointment_id: int, **body):
    """Send ``PATCH /appointments/{id}/reschedule``."""
    return api_client.patch(
        f"/appointments/{appointment_id}/reschedule", body, format="json"
    )
