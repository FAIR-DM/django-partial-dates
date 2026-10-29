"""Tests for the package's top-level module."""

import os
import subprocess
import sys
from importlib.metadata import version

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
