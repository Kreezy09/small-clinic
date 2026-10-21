"""GET /doctors/{id}/availability: listing a doctor's bookable slots on a date."""

from datetime import datetime

import pytest
import time_machine

from config.tests.helpers import NAIROBI, book, cancel

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]

MONDAY_STARTS = [
    "08:00",
    "08:30",
    "09:00",
    "09:30",
    "10:30",
    "11:00",
    "11:30",
    "12:00",
    "12:30",
]


def availability(api_client, doctor, day="2026-10-26"):
    return api_client.get(f"/doctors/{doctor.pk}/availability", {"date": day})


def slot_starts(response):
    return [slot["start_at"][11:16] for slot in response.json()["slots"]]


def test_lists_every_slot_of_working_hours(api_client, doctor):
    response = availability(api_client, doctor)

    assert response.status_code == 200
    body = response.json()
    assert body["doctor_id"] == doctor.pk
    assert body["date"] == "2026-10-26"
    assert body["slots"][0] == {
        "start_at": "2026-10-26T08:00:00+03:00",
        "end_at": "2026-10-26T08:30:00+03:00",
    }
    assert body["slots"][-1] == {
        "start_at": "2026-10-26T12:30:00+03:00",
        "end_at": "2026-10-26T13:00:00+03:00",
    }
    assert slot_starts(response) == MONDAY_STARTS


def test_booked_slot_is_not_listed(api_client, doctor, patient):
    book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")

    response = availability(api_client, doctor)

    assert slot_starts(response) == [s for s in MONDAY_STARTS if s != "09:00"]


def test_cancelled_appointment_keeps_slot_listed(api_client, doctor, patient):
    booked = book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    cancel(api_client, booked.json()["id"])

    response = availability(api_client, doctor)

    assert slot_starts(response) == MONDAY_STARTS


def test_other_doctors_bookings_do_not_affect_slots(
    api_client, doctor, other_doctor, patient
):
    book(api_client, other_doctor, patient, "2026-10-26T09:00:00+03:00")

    response = availability(api_client, doctor)

    assert slot_starts(response) == MONDAY_STARTS


def test_slots_overlapping_a_booking_of_another_length_are_not_listed(
    api_client, doctor, patient
):
    book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    doctor.slot_minutes = 20
    doctor.save()

    response = availability(api_client, doctor)

    assert slot_starts(response)[:5] == ["08:00", "08:20", "08:40", "09:40", "10:30"]


def test_slots_inside_lead_time_are_not_listed(api_client, doctor):
    with time_machine.travel(datetime(2026, 10, 26, 8, 10, tzinfo=NAIROBI), tick=False):
        response = availability(api_client, doctor)

    assert slot_starts(response)[0] == "09:30"


def test_every_listed_slot_can_be_booked(api_client, doctor, patient):
    first_slot = availability(api_client, doctor).json()["slots"][0]

    booking = book(api_client, doctor, patient, first_slot["start_at"])

    assert booking.status_code == 201
    assert first_slot not in availability(api_client, doctor).json()["slots"]


@pytest.mark.parametrize(
    "day",
    [
        pytest.param("2026-10-19", id="past-date"),
        pytest.param("2026-10-27", id="day-off"),
    ],
)
def test_no_slots_on_past_date_or_day_off(api_client, doctor, day):
    response = availability(api_client, doctor, day)

    assert response.status_code == 200
    assert response.json() == {"doctor_id": doctor.pk, "date": day, "slots": []}


def test_no_slots_when_doctor_not_accepting_appointments(api_client, doctor):
    doctor.accepting_appointments = False
    doctor.save()

    response = availability(api_client, doctor)

    assert response.json()["slots"] == []


def test_unknown_doctor_returns_not_found(api_client, doctor):
    response = api_client.get(
        f"/doctors/{doctor.pk + 1000}/availability", {"date": "2026-10-26"}
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "query",
    [pytest.param({}, id="missing"), pytest.param({"date": "26/10/2026"}, id="bad")],
)
def test_rejects_missing_or_malformed_date(api_client, doctor, query):
    response = api_client.get(f"/doctors/{doctor.pk}/availability", query)

    assert response.status_code == 400
    assert set(response.json()) == {"date"}
