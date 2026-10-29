"""Tests for the partial date value."""

import dataclasses

import pytest

from partial_dates import PartialDate, Precision


class TestBuilding:
    """A partial date holds the parts it was given and nothing more."""

    def test_a_year_alone_has_year_precision_and_unknown_month_and_day(self):
        value = PartialDate(1990)

        assert value.year == 1990
        assert value.month is None
        assert value.day is None
        assert value.precision is Precision.YEAR

    def test_a_year_and_month_has_month_precision_and_unknown_day(self):
        value = PartialDate(1990, 6)

        assert value.month == 6
        assert value.day is None
        assert value.precision is Precision.MONTH

    def test_a_full_date_has_day_precision(self):
        value = PartialDate(1990, 6, 14)

        assert value.day == 14
        assert value.precision is Precision.DAY

    @pytest.mark.parametrize("part", ["year", "month", "day"])
    def test_assigning_a_part_raises_and_leaves_the_value_unchanged(self, part):
        value = PartialDate(1990, 6, 14)

        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, part, 1991)

        assert value == PartialDate(1990, 6, 14)
