"""Clinic time zone and booking rules."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from config.settings.environment_settings import env

USE_TZ = True
CLINIC_TIMEZONE = ZoneInfo(env.str("CLINIC_TIMEZONE", default="Africa/Nairobi"))
TIME_ZONE = CLINIC_TIMEZONE.key

BOOKING_MIN_LEAD_TIME = timedelta(
    minutes=env.int("BOOKING_MIN_LEAD_MINUTES", default=60)
)
