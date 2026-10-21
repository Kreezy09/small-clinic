"""Repository-wide pytest fixtures."""

from datetime import timedelta

import pytest
import time_machine
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient

from config.tests.helpers import NAIROBI, NOW, create_doctor, create_patient
from doctors.models import Doctor
from patients.models import Patient


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
