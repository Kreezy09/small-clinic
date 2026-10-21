"""User model of the clinic: one row per person, with email as the login."""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import IntegrityError, models, transaction
from psycopg.errors import UniqueViolation

from accounts.exceptions import EmailTakenError

EMAIL_UNIQUE_CONSTRAINT = "accounts_user_email_unique"


class UserManager(BaseUserManager["User"]):
    """Creates users identified by email instead of username."""

    use_in_migrations = True

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: str | bool | None
    ) -> "User":
        """Create and save a user.

        Args:
            email: Login email; its domain is normalized to lower case.
            password: Raw password, or ``None`` to store an unusable password.
            **extra_fields: Other ``User`` field values.

        Returns:
            The saved user.

        Raises:
            EmailTakenError: Another user already has the email.
        """
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        try:
            with transaction.atomic(using=self._db):
                user.save(using=self._db)
        except IntegrityError as exc:
            cause = exc.__cause__
            if not (
                isinstance(cause, UniqueViolation)
                and cause.diag.constraint_name == EMAIL_UNIQUE_CONSTRAINT
            ):
                raise
            raise EmailTakenError("A user with this email already exists.") from exc
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: str | bool | None
    ) -> "User":
        """Create and save a staff superuser.

        Args:
            email: Login email; its domain is normalized to lower case.
            password: Raw password, or ``None`` to store an unusable password.
            **extra_fields: Other ``User`` field values.

        Returns:
            The saved user.

        Raises:
            EmailTakenError: Another user already has the email.
        """
        return self.create_user(
            email, password, is_staff=True, is_superuser=True, **extra_fields
        )


class User(AbstractUser):
    """A person known to the clinic, identified and logged in by email."""

    username = None
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name")

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = (
            models.UniqueConstraint(fields=["email"], name=EMAIL_UNIQUE_CONSTRAINT),
        )
