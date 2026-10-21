"""PostgreSQL connection settings."""

from config.settings.environment_settings import env

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("POSTGRES_DB"),
        "USER": env.str("POSTGRES_USER"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
        "HOST": env.str("POSTGRES_HOST", default="localhost"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "OPTIONS": {"sslmode": env.str("POSTGRES_SSLMODE", default="prefer")},
    }
}
