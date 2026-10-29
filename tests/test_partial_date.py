"""Tests for the partial date value."""

import dataclasses

import pytest

from partial_dates import PartialDate, Precision


class TestReadingTheIsoForm:
    """Reading accepts the three ISO forms and nothing else."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1990", PartialDate(1990)),
            ("1990-06", PartialDate(1990, 6)),
            ("1990-06-14", PartialDate(1990, 6, 14)),
            ("0001-01-01", PartialDate(1, 1, 1)),
        ],
    )
    def test_each_iso_form_equals_the_value_built_from_parts(self, text, expected):
        assert PartialDate.fromisoformat(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "1990-6",
            "19900614",
            "90",
            "1990-06-14T00:00",
            "1990?",
            "1990~",
            " 1990",
            "1990 ",
            "",
            "0000",
            "10000",
            "1990-13",
            "1990-02-30",
            "1990\n",
            "١٩٩٠",
            "1990-06-",
            "1990-",
        ],
    )
    def test_any_other_text_raises_value_error(self, text):
        with pytest.raises(ValueError):
            PartialDate.fromisoformat(text)

    @pytest.mark.parametrize("value", [1990, None, b"1990", 1990.0])
    def test_a_non_string_raises_value_error(self, value):
        with pytest.raises(ValueError):
            PartialDate.fromisoformat(value)


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

    @pytest.mark.parametrize(
        ("year", "month", "day"),
        [
            (1990, None, 14),
            (1990, 0, None),
            (1990, 13, None),
            (1990, 2, 30),
            (1990, 4, 31),
            (1990, 2, 29),
            (1900, 2, 29),
            (1990, 6, 0),
            (1990, 6, 32),
            (0, None, None),
            (10000, None, None),
            (-1, None, None),
            (None, 6, None),
            ("1990", None, None),
            (1990, "6", None),
            (1990, 6, "14"),
            (1990.0, None, None),
            (1990, 6.0, None),
            (1990, 6, 14.0),
            (True, None, None),
            (1990, True, None),
            (1990, 6, True),
        ],
    )
    def test_a_refused_combination_raises_value_error(self, year, month, day):
        with pytest.raises(ValueError):
            PartialDate(year, month, day)

    @pytest.mark.parametrize(
        ("year", "month", "day"),
        [(2000, 2, 29), (1, 1, 1), (9999, 12, 31), (1, None, None), (9999, 12, None)],
    )
    def test_the_boundary_values_build(self, year, month, day):
        value = PartialDate(year, month, day)

        assert (value.year, value.month, value.day) == (year, month, day)

    @pytest.mark.parametrize("part", ["year", "month", "day"])
    def test_assigning_a_part_raises_and_leaves_the_value_unchanged(self, part):
        value = PartialDate(1990, 6, 14)

        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, part, 1991)

        assert value == PartialDate(1990, 6, 14)
