"""POST /appointments: booking a doctor's slot."""

from datetime import datetime, timedelta

import pytest

from appointments.models import Appointment, AppointmentStatus
from config.tests.helpers import NAIROBI, book, cancel

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]


def test_books_free_slot(api_client, doctor, patient):
    response = book(
        api_client,
        doctor,
        patient,
        "2026-10-26T09:00:00+03:00",
        reason="Persistent cough",
    )

    assert response.status_code == 201
    appointment = Appointment.objects.get()
    assert response.json() == {
        "id": appointment.pk,
        "doctor_id": doctor.pk,
        "patient_id": patient.pk,
        "start_at": "2026-10-26T09:00:00+03:00",
        "end_at": "2026-10-26T09:30:00+03:00",
        "status": "BOOKED",
        "reason": "Persistent cough",
        "cancellation_reason": None,
        "cancelled_at": None,
    }
    assert appointment.start_at == datetime(2026, 10, 26, 9, 0, tzinfo=NAIROBI)
    assert appointment.status == AppointmentStatus.BOOKED


def test_accepts_start_in_any_utc_offset(api_client, doctor, patient):
    response = book(api_client, doctor, patient, "2026-10-26T06:00:00Z")

    assert response.status_code == 201
    assert response.json()["start_at"] == "2026-10-26T09:00:00+03:00"
    assert response.json()["reason"] is None


def test_slot_length_follows_doctor(api_client, doctor, patient):
    doctor.slot_minutes = 20
    doctor.save()

    response = book(api_client, doctor, patient, "2026-10-26T08:20:00+03:00")

    assert response.status_code == 201
    assert response.json()["end_at"] == "2026-10-26T08:40:00+03:00"


def test_back_to_back_slots_do_not_clash(api_client, doctor, patient, other_patient):
    first = book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    second = book(api_client, doctor, other_patient, "2026-10-26T09:30:00+03:00")

    assert first.status_code == 201
    assert second.status_code == 201


@pytest.mark.parametrize(
    "start_at",
    [
        pytest.param("2026-10-26T08:15:00+03:00", id="off-slot-grid"),
        pytest.param("2026-10-26T10:00:00+03:00", id="runs-into-break"),
        pytest.param("2026-10-26T10:15:00+03:00", id="during-break"),
        pytest.param("2026-10-26T13:00:00+03:00", id="after-hours"),
        pytest.param("2026-10-27T09:00:00+03:00", id="day-off"),
    ],
)
def test_rejects_time_outside_working_hours_slots(
    api_client, doctor, patient, start_at
):
    response = book(api_client, doctor, patient, start_at)

    assert response.status_code == 422
    assert response.json() == {
        "detail": "The requested time is not a slot within the doctor's working hours."
    }
    assert not Appointment.objects.exists()


def test_rejects_past_slot(api_client, doctor, patient):
    response = book(api_client, doctor, patient, "2026-10-19T09:00:00+03:00")

    assert response.status_code == 422
    assert response.json() == {"detail": "Appointments cannot be booked in the past."}


def test_rejects_slot_inside_lead_time(api_client, doctor, patient, settings):
    settings.BOOKING_MIN_LEAD_TIME = timedelta(minutes=90)

    response = book(api_client, doctor, patient, "2026-10-26T08:00:00+03:00")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Appointments must be booked at least 90 minutes ahead."
    }


def test_accepts_slot_exactly_at_lead_time(api_client, doctor, patient):
    response = book(api_client, doctor, patient, "2026-10-26T08:00:00+03:00")

    assert response.status_code == 201


def test_rejects_doctor_not_accepting_appointments(api_client, doctor, patient):
    doctor.accepting_appointments = False
    doctor.save()

    response = book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")

    assert response.status_code == 422
    assert response.json() == {"detail": "The doctor is not accepting appointments."}


def test_rejects_taken_slot(api_client, doctor, patient, other_patient):
    book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")

    response = book(api_client, doctor, other_patient, "2026-10-26T09:00:00+03:00")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The doctor already has an appointment in this slot."
    }
    assert Appointment.objects.count() == 1


def test_rejects_slot_overlapping_longer_appointment(
    api_client, doctor, patient, other_patient
):
    book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    doctor.slot_minutes = 20
    doctor.save()

    response = book(api_client, doctor, other_patient, "2026-10-26T09:20:00+03:00")

    assert response.status_code == 409


def test_cancelled_appointment_frees_slot(api_client, doctor, patient, other_patient):
    booked = book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    cancel(api_client, booked.json()["id"])

    response = book(api_client, doctor, other_patient, "2026-10-26T09:00:00+03:00")

    assert response.status_code == 201


def test_rejects_patient_booked_with_other_doctor(
    api_client, doctor, other_doctor, patient
):
    book(api_client, other_doctor, patient, "2026-10-26T09:00:00+03:00")

    response = book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The patient already has an appointment at this time."
    }


def test_rejects_unknown_doctor(api_client, doctor, patient):
    response = api_client.post(
        "/appointments",
        {
            "doctor_id": doctor.pk + 1000,
            "patient_id": patient.pk,
            "start_at": "2026-10-26T09:00:00+03:00",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "doctor_id" in response.json()


def test_rejects_missing_and_malformed_fields(api_client):
    response = api_client.post(
        "/appointments", {"start_at": "next monday"}, format="json"
    )

    assert response.status_code == 400
    assert set(response.json()) == {"doctor_id", "patient_id", "start_at"}
