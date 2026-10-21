"""Django admin: staff manage users, doctors, working hours and view appointments."""

from datetime import time

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from doctors.models import Doctor, Weekday
from tests.conftest import book

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]

MANAGEMENT = {
    "working_hours-MIN_NUM_FORMS": "0",
    "working_hours-MAX_NUM_FORMS": "1000",
}


def hours_rows(rows, initial=0):
    data = {
        **MANAGEMENT,
        "working_hours-TOTAL_FORMS": str(len(rows)),
        "working_hours-INITIAL_FORMS": str(initial),
    }
    for index, row in enumerate(rows):
        for field, value in row.items():
            data[f"working_hours-{index}-{field}"] = value
    return data


def monday(start, end):
    return {"iso_weekday": str(Weekday.MONDAY), "start_time": start, "end_time": end}


@pytest.fixture
def doctor_user(db):
    return get_user_model().objects.create_user(
        email="noor.doctor@example.test", first_name="Noor", last_name="Testdoctor"
    )


def test_createsuperuser_command_creates_staff_superuser():
    call_command(
        "createsuperuser",
        interactive=False,
        email="owner@example.test",
        first_name="Owner",
        last_name="Testadmin",
        verbosity=0,
    )

    user = get_user_model().objects.get(email="owner@example.test")
    assert user.is_staff
    assert user.is_superuser


def test_admin_requires_staff_login(client):
    response = client.get("/admin/doctors/doctor/")

    assert response.status_code == 302
    assert response.url.startswith("/admin/login/")


def test_staff_adds_user_without_password(staff_client):
    response = staff_client.post(
        "/admin/accounts/user/add/",
        {
            "email": "noor.doctor@example.test",
            "first_name": "Noor",
            "last_name": "Testdoctor",
            "phone": "",
            "usable_password": "false",
        },
    )

    assert response.status_code == 302
    user = get_user_model().objects.get(email="noor.doctor@example.test")
    assert not user.has_usable_password()
    assert not user.is_staff


def test_staff_adds_doctor_with_hours_that_become_bookable(
    staff_client, api_client, doctor_user
):
    response = staff_client.post(
        "/admin/doctors/doctor/add/",
        {
            "user": doctor_user.pk,
            "slot_minutes": "20",
            "accepting_appointments": "on",
            **hours_rows([monday("08:00", "09:00"), monday("10:00", "10:40")]),
        },
    )

    assert response.status_code == 302
    availability = api_client.get(
        f"/doctors/{doctor_user.pk}/availability", {"date": "2026-10-26"}
    )
    assert [slot["start_at"][11:16] for slot in availability.json()["slots"]] == [
        "08:00",
        "08:20",
        "08:40",
        "10:00",
        "10:20",
    ]


def test_rejects_overlapping_hours_on_new_doctor(staff_client, doctor_user):
    response = staff_client.post(
        "/admin/doctors/doctor/add/",
        {
            "user": doctor_user.pk,
            "slot_minutes": "30",
            "accepting_appointments": "on",
            **hours_rows([monday("08:00", "10:15"), monday("10:00", "12:00")]),
        },
    )

    assert response.status_code == 200
    assert (
        "Working hours overlap on Monday: 08:00-10:15 and 10:00-12:00."
        in response.content.decode()
    )
    assert not Doctor.objects.exists()


def existing_rows(doctor):
    return [
        {
            "id": str(block.pk),
            "doctor": str(doctor.pk),
            "iso_weekday": str(block.iso_weekday),
            "start_time": block.start_time.strftime("%H:%M"),
            "end_time": block.end_time.strftime("%H:%M"),
        }
        for block in doctor.working_hours.order_by("start_time")
    ]


def change_doctor(staff_client, doctor, rows, initial):
    return staff_client.post(
        f"/admin/doctors/doctor/{doctor.pk}/change/",
        {
            "slot_minutes": "30",
            "accepting_appointments": "on",
            **hours_rows(rows, initial=initial),
        },
    )


def test_rejects_block_overlapping_existing_hours(staff_client, doctor):
    rows = [*existing_rows(doctor), monday("12:30", "14:00")]

    response = change_doctor(staff_client, doctor, rows, initial=2)

    assert response.status_code == 200
    assert "Working hours overlap on Monday" in response.content.decode()
    assert doctor.working_hours.count() == 2


def test_deleted_block_does_not_count_as_overlap(staff_client, doctor):
    rows = existing_rows(doctor)
    rows[1]["DELETE"] = "on"
    rows.append(monday("10:15", "16:00"))

    response = change_doctor(staff_client, doctor, rows, initial=2)

    assert response.status_code == 302
    assert [
        (block.start_time, block.end_time)
        for block in doctor.working_hours.order_by("start_time")
    ] == [(time(8, 0), time(10, 15)), (time(10, 15), time(16, 0))]


def test_lists_doctors_and_patients(staff_client, doctor, patient):
    doctors = staff_client.get("/admin/doctors/doctor/")
    patients = staff_client.get("/admin/patients/patient/")

    assert "ada.doctor@example.test" in doctors.content.decode()
    assert "sam.patient@example.test" in patients.content.decode()


def test_appointments_are_view_only(staff_client, api_client, doctor, patient):
    appointment_id = book(
        api_client, doctor, patient, "2026-10-26T09:00:00+03:00"
    ).json()["id"]
    change_url = f"/admin/appointments/appointment/{appointment_id}/change/"

    listing = staff_client.get("/admin/appointments/appointment/")
    detail = staff_client.get(change_url)
    edit = staff_client.post(change_url, {"status": "CANCELLED"})
    add = staff_client.get("/admin/appointments/appointment/add/")
    delete = staff_client.post(
        f"/admin/appointments/appointment/{appointment_id}/delete/", {"post": "yes"}
    )

    assert listing.status_code == 200
    assert "sam.patient@example.test" in listing.content.decode()
    assert detail.status_code == 200
    assert "sam.patient@example.test with ada.doctor@example.test" in (
        detail.content.decode()
    )
    assert edit.status_code == 403
    assert add.status_code == 403
    assert delete.status_code == 403
