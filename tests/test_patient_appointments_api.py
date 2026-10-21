"""GET /patients/{id}/appointments: a patient's upcoming appointments."""

from datetime import datetime

import pytest
import time_machine

from tests.conftest import NAIROBI, book, cancel, reschedule

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]


def upcoming(api_client, patient):
    return api_client.get(f"/patients/{patient.pk}/appointments")


def starts(response):
    return [appointment["start_at"] for appointment in response.json()]


def test_lists_upcoming_appointments_by_start(
    api_client, doctor, other_doctor, patient
):
    later = book(api_client, doctor, patient, "2026-11-02T08:00:00+03:00")
    book(api_client, doctor, patient, "2026-10-26T11:00:00+03:00")
    book(api_client, other_doctor, patient, "2026-10-26T09:00:00+03:00")

    response = upcoming(api_client, patient)

    assert response.status_code == 200
    assert starts(response) == [
        "2026-10-26T09:00:00+03:00",
        "2026-10-26T11:00:00+03:00",
        "2026-11-02T08:00:00+03:00",
    ]
    assert response.json()[-1] == later.json()


def test_excludes_cancelled_appointments(api_client, doctor, patient):
    kept = book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    dropped = book(api_client, doctor, patient, "2026-10-26T11:00:00+03:00")
    cancel(api_client, dropped.json()["id"])

    response = upcoming(api_client, patient)

    assert [a["id"] for a in response.json()] == [kept.json()["id"]]


def test_excludes_appointments_that_have_started(api_client, doctor, patient):
    book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    book(api_client, doctor, patient, "2026-10-26T11:00:00+03:00")

    with time_machine.travel(datetime(2026, 10, 26, 9, 5, tzinfo=NAIROBI), tick=False):
        response = upcoming(api_client, patient)

    assert starts(response) == ["2026-10-26T11:00:00+03:00"]


def test_rescheduled_appointment_is_listed_at_new_time(api_client, doctor, patient):
    first = book(api_client, doctor, patient, "2026-10-26T09:00:00+03:00")
    book(api_client, doctor, patient, "2026-10-26T11:00:00+03:00")
    reschedule(api_client, first.json()["id"], start_at="2026-10-26T12:00:00+03:00")

    response = upcoming(api_client, patient)

    assert starts(response) == [
        "2026-10-26T11:00:00+03:00",
        "2026-10-26T12:00:00+03:00",
    ]


def test_excludes_other_patients_appointments(
    api_client, doctor, patient, other_patient
):
    book(api_client, doctor, other_patient, "2026-10-26T09:00:00+03:00")

    response = upcoming(api_client, patient)

    assert response.status_code == 200
    assert response.json() == []


def test_query_count_does_not_grow_with_appointments(
    api_client, doctor, patient, django_assert_num_queries
):
    for start in ("08:00", "09:00", "11:00", "12:00"):
        book(api_client, doctor, patient, f"2026-10-26T{start}:00+03:00")

    with django_assert_num_queries(2):
        response = upcoming(api_client, patient)

    assert len(response.json()) == 4


def test_unknown_patient_returns_not_found(api_client, patient):
    response = api_client.get(f"/patients/{patient.pk + 1000}/appointments")

    assert response.status_code == 404
