"""manage.py createsuperuser: creating the first staff account."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

pytestmark = pytest.mark.django_db


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
