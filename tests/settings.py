"""Django settings for the test suite."""

import os

SECRET_KEY = "tests-only-not-a-secret"
INSTALLED_APPS = ["django.contrib.contenttypes", "tests", "tests.moving"]
if os.environ.get("TEST_DATABASE") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("PGDATABASE"),
            "USER": os.environ.get("PGUSER"),
            "PASSWORD": os.environ.get("PGPASSWORD"),
            "HOST": os.environ.get("PGHOST"),
            "PORT": os.environ.get("PGPORT"),
        }
    }
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
    }
USE_TZ = True
# Django 6.0 made BigAutoField the default. Naming it keeps the test migration the
# same on Django 5.2.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
