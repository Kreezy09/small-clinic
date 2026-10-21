"""POST /patients: registering a patient."""

import pytest
from django.contrib.auth import get_user_model

from patients.models import Patient

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]


def register(api_client, **body):
    return api_client.post("/patients", body, format="json")


def test_registers_patient(api_client):
    response = register(
        api_client,
        email="Riley@EXAMPLE.TEST",
        first_name="Riley",
        last_name="Testpatient",
        phone="+254700000001",
    )

    assert response.status_code == 201
    patient = Patient.objects.get()
    assert response.json() == {
        "id": patient.pk,
        "email": "Riley@example.test",
        "first_name": "Riley",
        "last_name": "Testpatient",
        "phone": "+254700000001",
    }
    assert not patient.user.has_usable_password()


def test_phone_is_optional(api_client):
    response = register(
        api_client,
        email="riley@example.test",
        first_name="Riley",
        last_name="Testpatient",
    )

    assert response.status_code == 201
    assert response.json()["phone"] is None


def test_registered_patient_can_book(api_client, doctor):
    patient_id = register(
        api_client,
        email="riley@example.test",
        first_name="Riley",
        last_name="Testpatient",
    ).json()["id"]

    response = api_client.post(
        "/appointments",
        {
            "doctor_id": doctor.pk,
            "patient_id": patient_id,
            "start_at": "2026-10-26T09:00:00+03:00",
        },
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    "email",
    [
        pytest.param("sam.patient@example.test", id="existing-patient"),
        pytest.param("ada.doctor@example.test", id="existing-doctor"),
    ],
)
def test_rejects_email_already_in_use(api_client, patient, doctor, email):
    response = register(
        api_client, email=email, first_name="Riley", last_name="Testpatient"
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "A user with this email already exists."}
    assert get_user_model().objects.count() == 2


def test_rejects_invalid_and_missing_fields(api_client):
    response = register(api_client, email="not-an-email", phone="")

    assert response.status_code == 400
    assert set(response.json()) == {"email", "first_name", "last_name", "phone"}
    assert not Patient.objects.exists()
