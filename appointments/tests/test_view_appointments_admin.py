"""Django admin: staff view appointments without changing them."""

import pytest

from config.tests.helpers import book

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("frozen_clock")]


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
