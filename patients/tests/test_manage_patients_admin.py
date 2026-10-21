"""Django admin: staff list patients."""

import pytest

pytestmark = pytest.mark.django_db


def test_lists_patients(staff_client, patient):
    response = staff_client.get("/admin/patients/patient/")

    assert "sam.patient@example.test" in response.content.decode()
