"""Django admin: staff log in and manage user accounts."""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


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
