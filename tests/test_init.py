"""Tests for the package's top-level module."""

import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import partial_dates


class TestVersion:
    """The package reports the version it was installed as."""

    def test_version_matches_the_installed_distribution(self):
        assert partial_dates.__version__ == version("django-partial-dates")


class TestImportWithoutSettings:
    def test_a_fresh_interpreter_imports_it_and_builds_a_value(self):
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        code = "import partial_dates; partial_dates.PartialDate(1990)"

        result = subprocess.run([sys.executable, "-c", code], env=env, check=False)

        assert result.returncode == 0


SOURCE = """
import sys

sys.modules["django_filters"] = None
sys.modules["rest_framework"] = None
import django

django.setup()
import partial_dates
import partial_dates.fields
import partial_dates.forms
from tests.models import Sample

assert partial_dates.PartialDate(1990, 6).isoformat() == "1990-06"
field = Sample._meta.get_field("collected")
assert field.to_python("1990") == partial_dates.PartialDate(1990)
"""


class TestImportWithoutExtras:
    def test_a_fresh_interpreter_with_both_blocked_imports_and_builds_a_value(self):
        env = {**os.environ, "DJANGO_SETTINGS_MODULE": "tests.settings"}
        root = Path(__file__).parent.parent

        result = subprocess.run(
            [sys.executable, "-c", SOURCE],
            env=env,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
