"""HTTPS proxy and cookie security settings."""

from config.settings.environment_settings import env

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_COOKIES = env.bool("DJANGO_SECURE_COOKIES", default=True)
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
