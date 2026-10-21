"""PATCH /appointments/{id}/cancel: cancelling an appointment."""

import pytest

from appointments.models import Appointment, AppointmentStatus
from tests.conftest import NOW, book, cancel

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]

SLOT = "2026-10-26T09:00:00+03:00"


@pytest.fixture
def appointment_id(api_client, doctor, patient):
    return book(api_client, doctor, patient, SLOT, reason="Checkup").json()["id"]


def test_cancels_booked_appointment(api_client, doctor, patient, appointment_id):
    response = cancel(api_client, appointment_id, reason="Feeling better")

    assert response.status_code == 200
    assert response.json() == {
        "id": appointment_id,
        "doctor_id": doctor.pk,
        "patient_id": patient.pk,
        "start_at": "2026-10-26T09:00:00+03:00",
        "end_at": "2026-10-26T09:30:00+03:00",
        "status": "CANCELLED",
        "reason": "Checkup",
        "cancellation_reason": "Feeling better",
        "cancelled_at": "2026-10-26T07:00:00+03:00",
    }
    appointment = Appointment.objects.get(pk=appointment_id)
    assert appointment.status == AppointmentStatus.CANCELLED
    assert appointment.cancelled_at == NOW


def test_reason_is_optional(api_client, appointment_id):
    response = cancel(api_client, appointment_id)

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancellation_reason"] is None


def test_rejects_already_cancelled(api_client, appointment_id):
    cancel(api_client, appointment_id, reason="Feeling better")

    response = cancel(api_client, appointment_id, reason="Second attempt")

    assert response.status_code == 409
    assert response.json() == {"detail": "The appointment is already cancelled."}
    appointment = Appointment.objects.get(pk=appointment_id)
    assert appointment.cancellation_reason == "Feeling better"


def test_cancelled_slot_is_bookable_again(
    api_client, doctor, other_patient, appointment_id
):
    cancel(api_client, appointment_id, reason="Feeling better")

    availability = api_client.get(
        f"/doctors/{doctor.pk}/availability", {"date": "2026-10-26"}
    )
    rebooking = book(api_client, doctor, other_patient, SLOT)

    assert SLOT in [slot["start_at"] for slot in availability.json()["slots"]]
    assert rebooking.status_code == 201


def test_cancelling_frees_the_patient(
    api_client, other_doctor, patient, appointment_id
):
    cancel(api_client, appointment_id)

    response = book(api_client, other_doctor, patient, SLOT)

    assert response.status_code == 201


def test_unknown_appointment_returns_not_found(api_client, appointment_id):
    response = cancel(api_client, appointment_id + 1000, reason="Feeling better")

    assert response.status_code == 404


def test_rejects_blank_reason(api_client, appointment_id):
    response = cancel(api_client, appointment_id, reason="   ")

    assert response.status_code == 400
    assert set(response.json()) == {"reason"}
    assert Appointment.objects.get(pk=appointment_id).status == AppointmentStatus.BOOKED
