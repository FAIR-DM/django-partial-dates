"""Django settings for the test suite."""

SECRET_KEY = "tests-only-not-a-secret"
INSTALLED_APPS = ["django.contrib.contenttypes"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
USE_TZ = True
