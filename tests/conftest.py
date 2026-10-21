"""Shared fixtures: clinic settings, an API client, synthetic doctors and patients."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient

from doctors.models import Doctor, Weekday
from patients.models import Patient

NAIROBI = ZoneInfo("Africa/Nairobi")
NOW = datetime(2026, 10, 26, 7, 0, tzinfo=NAIROBI)


@pytest.fixture(autouse=True)
def clinic_settings(settings, tmp_path):
    settings.STATIC_ROOT = tmp_path
    settings.CLINIC_TIMEZONE = NAIROBI
    settings.BOOKING_MIN_LEAD_TIME = timedelta(hours=1)
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }


@pytest.fixture
def frozen_clock():
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def staff_client(db) -> Client:
    staff = get_user_model().objects.create_superuser(
        email="staff@example.test", first_name="Sky", last_name="Testadmin"
    )
    client = Client()
    client.force_login(staff)
    return client


def book(api_client, doctor, patient, start_at, **extra):
    payload = {
        "doctor_id": doctor.pk,
        "patient_id": patient.pk,
        "start_at": start_at,
        **extra,
    }
    return api_client.post("/appointments", payload, format="json")


def cancel(api_client, appointment_id, **body):
    return api_client.patch(
        f"/appointments/{appointment_id}/cancel", body, format="json"
    )


def create_doctor(email: str, first_name: str) -> Doctor:
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
    user = get_user_model().objects.create_user(
        email=email, first_name=first_name, last_name="Testpatient"
    )
    return Patient.objects.create(user=user)


@pytest.fixture
def doctor(db) -> Doctor:
    return create_doctor("ada.doctor@example.test", "Ada")


@pytest.fixture
def other_doctor(db) -> Doctor:
    return create_doctor("grace.doctor@example.test", "Grace")


@pytest.fixture
def patient(db) -> Patient:
    return create_patient("sam.patient@example.test", "Sam")


@pytest.fixture
def other_patient(db) -> Patient:
    return create_patient("alex.patient@example.test", "Alex")


def reschedule(api_client, appointment_id, **body):
    return api_client.patch(
        f"/appointments/{appointment_id}/reschedule", body, format="json"
    )
