"""Admin for doctors and their weekly working hours."""

from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest

from doctors.models import Doctor, DoctorWorkingHours


class WorkingHoursFormSet(BaseInlineFormSet):
    """Rejects working-hours blocks that overlap on the same weekday."""

    def clean(self) -> None:
        """Validate the blocks kept after this save."""
        super().clean()
        if any(self.errors):
            return
        kept = [
            form.instance
            for form in self.forms
            if (form.instance.pk or form.has_changed())
            and not self._should_delete_form(form)
        ]
        DoctorWorkingHours.ensure_no_overlap(kept)


class DoctorWorkingHoursInline(admin.TabularInline):
    """Edits a doctor's working-hours blocks on the doctor page."""

    model = DoctorWorkingHours
    formset = WorkingHoursFormSet
    fields = ("iso_weekday", "start_time", "end_time")
    ordering = ("iso_weekday", "start_time")
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """Manages doctors, their booking settings and working hours."""

    fields = ("user", "slot_minutes", "accepting_appointments")
    autocomplete_fields = ("user",)
    list_display = ("user", "slot_minutes", "accepting_appointments")
    list_filter = ("accepting_appointments",)
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_select_related = ("user",)
    inlines = (DoctorWorkingHoursInline,)

    def get_readonly_fields(
        self, request: HttpRequest, obj: Doctor | None = None
    ) -> tuple[str, ...]:
        """Lock the user once the doctor exists."""
        return ("user",) if obj else ()
