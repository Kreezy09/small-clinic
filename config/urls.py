"""Root URL routes of the clinic booking API."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("appointments.urls")),
    path("", include("doctors.urls")),
    path("", include("patients.urls")),
]
