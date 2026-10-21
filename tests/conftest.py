"""Shared fixtures: clinic settings, an API client, synthetic doctors and patients."""

from datetime import time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from doctors.models import Doctor, Weekday
from patients.models import Patient

NAIROBI = ZoneInfo("Africa/Nairobi")


@pytest.fixture(autouse=True)
def clinic_settings(settings):
    settings.CLINIC_TIMEZONE = NAIROBI
    settings.BOOKING_MIN_LEAD_TIME = timedelta(hours=1)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


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
