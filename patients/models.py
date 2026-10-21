"""Patient profile of a clinic user."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, models, transaction
from psycopg.errors import UniqueViolation

from core.models import TimestampedModel
from patients.exceptions import EmailTakenError

EMAIL_UNIQUE_CONSTRAINT = "accounts_user_email_key"


class Patient(TimestampedModel):
    """Marks a user as someone who books appointments."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        primary_key=True,
        related_name="patient",
    )

    def __str__(self) -> str:
        return str(self.user)

    @classmethod
    def register(
        cls, email: str, first_name: str, last_name: str, phone: str | None
    ) -> "Patient":
        """Create a patient and its user, without a usable password.

        Args:
            email: Login email of the new user.
            first_name: Patient's first name.
            last_name: Patient's last name.
            phone: Contact phone number.

        Returns:
            The saved patient.

        Raises:
            EmailTakenError: Another user already has the email.
        """
        try:
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    email=email, first_name=first_name, last_name=last_name, phone=phone
                )
                return cls.objects.create(user=user)
        except IntegrityError as exc:
            cause = exc.__cause__
            if not (
                isinstance(cause, UniqueViolation)
                and cause.diag.constraint_name == EMAIL_UNIQUE_CONSTRAINT
            ):
                raise
            raise EmailTakenError("A user with this email already exists.") from exc
