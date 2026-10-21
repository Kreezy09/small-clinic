"""Doctor API routes."""

from rest_framework.routers import SimpleRouter

from doctors.views import DoctorViewSet

router = SimpleRouter(trailing_slash=False)
router.register("doctors", DoctorViewSet, basename="doctor")

urlpatterns = router.urls
