"""Concurrent requests for overlapping slots: exactly one wins, the rest get 409."""

import threading
from collections import Counter

import pytest
from django.db import connection
from rest_framework.test import APIClient

from config.tests.helpers import create_patient

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("frozen_clock"),
]

CONTENDERS = 12
MONDAY_SLOTS = [
    f"{day}T{start}:00+03:00"
    for day in ("2026-10-26", "2026-11-02", "2026-11-09")
    for start in ("08:00", "08:30", "09:00", "09:30", "10:30", "11:00", "11:30")
]


def run_concurrently(requests):
    barrier = threading.Barrier(len(requests))
    outcomes = []
    lock = threading.Lock()

    def worker(request):
        client = APIClient(raise_request_exception=False)
        barrier.wait()
        try:
            status = request(client).status_code
        finally:
            connection.close()
        with lock:
            outcomes.append(status)

    threads = [threading.Thread(target=worker, args=(r,)) for r in requests]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return Counter(outcomes)


def booking(doctor, patient, start_at):
    def request(client):
        return client.post(
            "/appointments",
            {"doctor_id": doctor.pk, "patient_id": patient.pk, "start_at": start_at},
            format="json",
        )

    return request


def test_concurrent_bookings_of_one_slot(doctor):
    patients = [
        create_patient(f"race{index}.patient@example.test", f"Race{index}")
        for index in range(CONTENDERS)
    ]
    for start_at in MONDAY_SLOTS:
        outcomes = run_concurrently(
            [booking(doctor, patient, start_at) for patient in patients]
        )

        assert outcomes == Counter({201: 1, 409: CONTENDERS - 1})


def test_concurrent_bookings_of_one_patient_with_different_doctors(
    doctor, other_doctor, patient
):
    outcomes = run_concurrently(
        [
            booking(doctor, patient, "2026-10-26T09:00:00+03:00"),
            booking(other_doctor, patient, "2026-10-26T09:00:00+03:00"),
        ]
        * 6
    )

    assert outcomes == Counter({201: 1, 409: 11})
