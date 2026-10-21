"""Patient API routes."""

from rest_framework.routers import SimpleRouter

from patients.views import PatientViewSet

router = SimpleRouter(trailing_slash=False)
router.register("patients", PatientViewSet, basename="patient")

urlpatterns = router.urls
