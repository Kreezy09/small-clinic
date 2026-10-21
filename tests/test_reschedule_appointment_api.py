"""PATCH /appointments/{id}/reschedule: moving an appointment to a new slot."""

from datetime import datetime

import pytest

from appointments.models import Appointment, AppointmentStatus
from tests.conftest import NAIROBI, book, cancel, reschedule

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]

OLD_SLOT = "2026-10-26T09:00:00+03:00"
NEW_SLOT = "2026-10-26T11:00:00+03:00"


@pytest.fixture
def appointment_id(api_client, doctor, patient):
    return book(api_client, doctor, patient, OLD_SLOT, reason="Checkup").json()["id"]


def listed_starts(api_client, doctor):
    response = api_client.get(
        f"/doctors/{doctor.pk}/availability", {"date": "2026-10-26"}
    )
    return [slot["start_at"] for slot in response.json()["slots"]]


def assert_unchanged(appointment_id, doctor):
    appointment = Appointment.objects.get(pk=appointment_id)
    assert appointment.doctor == doctor
    assert appointment.start_at == datetime(2026, 10, 26, 9, 0, tzinfo=NAIROBI)


def test_moves_appointment_to_new_slot(api_client, doctor, patient, appointment_id):
    response = reschedule(api_client, appointment_id, start_at=NEW_SLOT)

    assert response.status_code == 200
    assert response.json() == {
        "id": appointment_id,
        "doctor_id": doctor.pk,
        "patient_id": patient.pk,
        "start_at": "2026-10-26T11:00:00+03:00",
        "end_at": "2026-10-26T11:30:00+03:00",
        "status": "BOOKED",
        "reason": "Checkup",
        "cancellation_reason": None,
        "cancelled_at": None,
    }
    assert Appointment.objects.count() == 1


def test_original_slot_becomes_available(
    api_client, doctor, other_patient, appointment_id
):
    reschedule(api_client, appointment_id, start_at=NEW_SLOT)

    starts = listed_starts(api_client, doctor)
    rebooking = book(api_client, doctor, other_patient, OLD_SLOT)

    assert OLD_SLOT in starts
    assert NEW_SLOT not in starts
    assert rebooking.status_code == 201


def test_moves_to_another_doctor(api_client, doctor, other_doctor, appointment_id):
    other_doctor.slot_minutes = 20
    other_doctor.save()

    response = reschedule(
        api_client, appointment_id, doctor_id=other_doctor.pk, start_at=OLD_SLOT
    )

    assert response.status_code == 200
    assert response.json()["doctor_id"] == other_doctor.pk
    assert response.json()["end_at"] == "2026-10-26T09:20:00+03:00"
    assert OLD_SLOT in listed_starts(api_client, doctor)
    assert OLD_SLOT not in listed_starts(api_client, other_doctor)


def test_may_move_into_its_own_current_time(api_client, doctor, appointment_id):
    doctor.slot_minutes = 20
    doctor.save()

    response = reschedule(
        api_client, appointment_id, start_at="2026-10-26T09:20:00+03:00"
    )

    assert response.status_code == 200
    assert response.json()["end_at"] == "2026-10-26T09:40:00+03:00"


@pytest.mark.parametrize(
    ("start_at", "detail"),
    [
        pytest.param(
            "2026-10-26T10:15:00+03:00",
            "The requested time is not a slot within the doctor's working hours.",
            id="outside-working-hours",
        ),
        pytest.param(
            "2026-10-19T09:00:00+03:00",
            "Appointments cannot be booked in the past.",
            id="past",
        ),
    ],
)
def test_rejects_unbookable_new_slot(
    api_client, doctor, appointment_id, start_at, detail
):
    response = reschedule(api_client, appointment_id, start_at=start_at)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    assert_unchanged(appointment_id, doctor)


def test_rejects_new_slot_inside_lead_time(
    api_client, doctor, appointment_id, settings
):
    settings.BOOKING_MIN_LEAD_TIME = settings.BOOKING_MIN_LEAD_TIME * 2

    response = reschedule(
        api_client, appointment_id, start_at="2026-10-26T08:30:00+03:00"
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Appointments must be booked at least 120 minutes ahead."
    }


def test_rejects_slot_taken_by_another_patient(
    api_client, doctor, other_patient, appointment_id
):
    book(api_client, doctor, other_patient, NEW_SLOT)

    response = reschedule(api_client, appointment_id, start_at=NEW_SLOT)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The doctor already has an appointment in this slot."
    }
    assert_unchanged(appointment_id, doctor)


def test_rejects_slot_where_patient_is_busy(
    api_client, doctor, other_doctor, patient, appointment_id
):
    book(api_client, other_doctor, patient, NEW_SLOT)

    response = reschedule(api_client, appointment_id, start_at=NEW_SLOT)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The patient already has an appointment at this time."
    }


def test_rejects_doctor_not_accepting_appointments(
    api_client, doctor, other_doctor, appointment_id
):
    other_doctor.accepting_appointments = False
    other_doctor.save()

    response = reschedule(
        api_client, appointment_id, doctor_id=other_doctor.pk, start_at=NEW_SLOT
    )

    assert response.status_code == 422
    assert_unchanged(appointment_id, doctor)


def test_rejects_cancelled_appointment(api_client, doctor, appointment_id):
    cancel(api_client, appointment_id)

    response = reschedule(api_client, appointment_id, start_at=NEW_SLOT)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Cancelled appointments cannot be rescheduled."
    }
    appointment = Appointment.objects.get(pk=appointment_id)
    assert appointment.status == AppointmentStatus.CANCELLED
    assert_unchanged(appointment_id, doctor)


def test_unknown_appointment_returns_not_found(api_client, appointment_id):
    response = reschedule(api_client, appointment_id + 1000, start_at=NEW_SLOT)

    assert response.status_code == 404


def test_rejects_missing_start_and_unknown_doctor(api_client, doctor, appointment_id):
    response = reschedule(api_client, appointment_id, doctor_id=doctor.pk + 1000)

    assert response.status_code == 400
    assert set(response.json()) == {"doctor_id", "start_at"}
