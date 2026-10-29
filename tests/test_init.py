"""Tests for the package's top-level module."""

from importlib.metadata import version

import partial_dates


class TestVersion:
    """The package reports the version it was installed as."""

    def test_version_matches_the_installed_distribution(self):
        assert partial_dates.__version__ == version("django-partial-dates")
