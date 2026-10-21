"""Admin for patients."""

from django.contrib import admin

from patients.models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Lists and edits patients."""

    fields = ("user",)
    autocomplete_fields = ("user",)
    list_display = ("user", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_select_related = ("user",)
