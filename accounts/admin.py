"""Admin for email-based user accounts."""

from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import forms as auth_forms

from accounts.models import User


class UserCreationForm(auth_forms.AdminUserCreationForm):
    """Admin form that creates a user identified by email."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone")


class UserChangeForm(auth_forms.UserChangeForm):
    """Admin form that edits a user identified by email."""

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
            "last_login",
            "date_joined",
        )


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    """Manages users; a password login is optional for doctors and patients."""

    form = UserChangeForm
    add_form = UserCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    list_display = ("email", "first_name", "last_name", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
