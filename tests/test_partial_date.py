"""Tests for the partial date value."""

import calendar
import dataclasses
import datetime

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


class TestWritingTheIsoForm:
    """A partial date writes the ISO form it was recorded at."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (PartialDate(1990), "1990"),
            (PartialDate(1990, 6), "1990-06"),
            (PartialDate(1990, 6, 14), "1990-06-14"),
            (PartialDate(990), "0990"),
            (PartialDate(1, 1, 1), "0001-01-01"),
        ],
    )
    def test_each_precision_writes_its_form(self, value, expected):
        assert value.isoformat() == expected
        assert str(value) == expected

    def test_every_value_in_the_sample_years_round_trips(self):
        for year in (1, 1999, 2000, 9999):
            days = [
                PartialDate(year, month, day)
                for month in range(1, 13)
                for day in range(1, calendar.monthrange(year, month)[1] + 1)
            ]
            months = [PartialDate(year, month) for month in range(1, 13)]
            for value in [PartialDate(year), *months, *days]:
                text = value.isoformat()

                read = PartialDate.fromisoformat(text)

                assert read == value
                assert read.isoformat() == text


def every_value_in_years(*years):
    values = []
    for year in years:
        values.append(PartialDate(year))
        for month in range(1, 13):
            values.append(PartialDate(year, month))
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                values.append(PartialDate(year, month, day))
    return values


def pair_sample():
    values = []
    for year in (1999, 2000):
        values.append(PartialDate(year))
        for month in (1, 2, 12):
            values.append(PartialDate(year, month))
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                values.append(PartialDate(year, month, day))
    return values


class TestOrdering:
    """Values sort in the order of their ISO forms, coarse before fine."""

    def test_mixed_precisions_sort_in_iso_order(self):
        values = [
            PartialDate(1991),
            PartialDate(1990, 6, 14),
            PartialDate(1990),
            PartialDate(1990, 6),
        ]

        assert sorted(values) == [
            PartialDate(1990),
            PartialDate(1990, 6),
            PartialDate(1990, 6, 14),
            PartialDate(1991),
        ]

    def test_every_value_in_two_years_sorts_as_its_iso_text(self):
        values = every_value_in_years(1999, 2000)

        assert len(values) == 757
        assert sorted(reversed(values)) == sorted(values, key=PartialDate.isoformat)

    def test_each_operator_agrees_with_iso_text_over_every_pair(self):
        values = pair_sample()

        for left in values:
            for right in values:
                left_text, right_text = left.isoformat(), right.isoformat()
                assert (left < right) == (left_text < right_text)
                assert (left <= right) == (left_text <= right_text)
                assert (left > right) == (left_text > right_text)
                assert (left >= right) == (left_text >= right_text)

    @pytest.mark.parametrize(
        "other",
        [datetime.date(1990, 6, 14), "1990-06-14", 1990],
        ids=["date", "str", "int"],
    )
    def test_ordering_against_another_type_raises_type_error(self, other):
        value = PartialDate(1990, 6, 14)

        with pytest.raises(TypeError):
            value < other
        with pytest.raises(TypeError):
            value <= other
        with pytest.raises(TypeError):
            value > other
        with pytest.raises(TypeError):
            value >= other
        with pytest.raises(TypeError):
            other < value
        with pytest.raises(TypeError):
            other <= value
        with pytest.raises(TypeError):
            other > value
        with pytest.raises(TypeError):
            other >= value


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
