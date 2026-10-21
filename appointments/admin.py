"""Read-only admin for appointments; changes go through the booking API."""

from django.contrib import admin
from django.http import HttpRequest

from appointments.models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Lists appointments without allowing changes that bypass booking rules."""

    list_display = ("id", "doctor", "patient", "start_at", "end_at", "status")
    list_filter = ("status", "doctor")
    search_fields = ("patient__user__email", "doctor__user__email")
    date_hierarchy = "start_at"
    list_select_related = ("doctor__user", "patient__user")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Disallow creating appointments outside the booking API."""
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Appointment | None = None
    ) -> bool:
        """Disallow editing appointments outside the booking API."""
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Appointment | None = None
    ) -> bool:
        """Disallow deleting appointments; cancel them instead."""
        return False
