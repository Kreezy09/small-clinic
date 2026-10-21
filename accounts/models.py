"""User model of the clinic: one row per person, with email as the login."""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


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
        """
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
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
        """
        return self.create_user(
            email, password, is_staff=True, is_superuser=True, **extra_fields
        )


class User(AbstractUser):
    """A person known to the clinic, identified and logged in by email."""

    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name")

    objects = UserManager()
