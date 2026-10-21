"""Patient profile of a clinic user."""

from django.conf import settings
from django.db import models

from core.models import TimestampedModel


class Patient(TimestampedModel):
    """Marks a user as someone who books appointments."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        primary_key=True,
        related_name="patient",
    )
