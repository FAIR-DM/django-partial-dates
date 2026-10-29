"""Tests for the partial date value."""

import calendar
import dataclasses
import datetime
import operator

import pytest

from partial_dates import PartialDate, Precision, Relation


class TestReadingTheIsoForm:
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
        shuffled = values[1::2] + values[::2]

        assert sorted(shuffled) == sorted(values, key=PartialDate.isoformat)

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
    @pytest.mark.parametrize(
        "compare", [operator.lt, operator.le, operator.gt, operator.ge]
    )
    def test_ordering_against_another_type_raises_type_error(self, compare, other):
        value = PartialDate(1990, 6, 14)

        with pytest.raises(TypeError):
            compare(value, other)
        with pytest.raises(TypeError):
            compare(other, value)


class TestEquality:
    @pytest.mark.parametrize(
        ("year", "month", "day"), [(1990, None, None), (1990, 6, None), (1990, 6, 14)]
    )
    def test_the_same_parts_are_equal_with_equal_hashes(self, year, month, day):
        left = PartialDate(year, month, day)
        right = PartialDate(year, month, day)

        assert left == right
        assert hash(left) == hash(right)

    @pytest.mark.parametrize(
        ("coarse", "fine"),
        [
            (PartialDate(1990), PartialDate(1990, 1, 1)),
            (PartialDate(1990, 6), PartialDate(1990, 6, 1)),
        ],
    )
    def test_a_value_is_not_equal_to_the_same_value_at_finer_precision(
        self, coarse, fine
    ):
        assert coarse != fine

    def test_equal_values_built_separately_are_one_set_member(self):
        values = {
            PartialDate(1990, 6, 14),
            PartialDate(1990, 6, 14),
            PartialDate.fromisoformat("1990-06-14"),
        }

        assert values == {PartialDate(1990, 6, 14)}
        assert len(values) == 1

    def test_equal_values_built_separately_are_one_dict_key(self):
        values = {PartialDate(1990, 6): "first"}
        values[PartialDate.fromisoformat("1990-06")] = "second"

        assert values == {PartialDate(1990, 6): "second"}

    @pytest.mark.parametrize(
        "other",
        [datetime.date(1990, 6, 14), "1990-06-14", 1990],
        ids=["date", "str", "int"],
    )
    def test_a_value_is_not_equal_to_another_type(self, other):
        value = PartialDate(1990, 6, 14)

        assert value != other
        assert other != value


class TestPeriod:
    @pytest.mark.parametrize(
        ("value", "start", "end"),
        [
            (PartialDate(1990), datetime.date(1990, 1, 1), datetime.date(1990, 12, 31)),
            (
                PartialDate(1990, 6),
                datetime.date(1990, 6, 1),
                datetime.date(1990, 6, 30),
            ),
            (
                PartialDate(1990, 6, 14),
                datetime.date(1990, 6, 14),
                datetime.date(1990, 6, 14),
            ),
            (
                PartialDate(1990, 2),
                datetime.date(1990, 2, 1),
                datetime.date(1990, 2, 28),
            ),
            (
                PartialDate(2000, 2),
                datetime.date(2000, 2, 1),
                datetime.date(2000, 2, 29),
            ),
            (
                PartialDate(1900, 2),
                datetime.date(1900, 2, 1),
                datetime.date(1900, 2, 28),
            ),
            (PartialDate(1), datetime.date(1, 1, 1), datetime.date(1, 12, 31)),
            (PartialDate(9999), datetime.date(9999, 1, 1), datetime.date(9999, 12, 31)),
        ],
    )
    def test_start_and_end_are_the_first_and_last_day_of_the_period(
        self, value, start, end
    ):
        assert value.start == start
        assert value.end == end
        assert type(value.start) is datetime.date
        assert type(value.end) is datetime.date

    def test_start_and_end_of_every_value_in_two_years_are_its_first_and_last_day(
        self,
    ):
        one_day = datetime.timedelta(days=1)
        for value in every_value_in_years(1999, 2000):
            text = value.isoformat()
            assert value.start.isoformat().startswith(text)
            assert value.end.isoformat().startswith(text)
            assert not (value.start - one_day).isoformat().startswith(text)
            assert not (value.end + one_day).isoformat().startswith(text)


def parts_known(value):
    return 1 + (value.month is not None) + (value.day is not None)


def is_earlier_at_the_coarser_precision(first, second):
    known = min(parts_known(first), parts_known(second))
    first_parts = (first.year, first.month, first.day)[:known]
    second_parts = (second.year, second.month, second.day)[:known]
    return first_parts < second_parts


class TestRelation:
    @pytest.mark.parametrize(
        ("first", "second", "expected"),
        [
            (PartialDate(1990, 6), PartialDate(1991), Relation.BEFORE),
            (PartialDate(1991), PartialDate(1990, 6), Relation.AFTER),
            (PartialDate(1990), PartialDate(1990, 6), Relation.OVERLAPPING),
            (PartialDate(1990, 6), PartialDate(1990), Relation.OVERLAPPING),
            (PartialDate(1990, 6), PartialDate(1990, 6, 14), Relation.OVERLAPPING),
            (PartialDate(1990, 6, 14), PartialDate(1990, 6), Relation.OVERLAPPING),
            (PartialDate(1990, 6), PartialDate(1990, 6), Relation.OVERLAPPING),
            (PartialDate(1990), PartialDate(1990), Relation.OVERLAPPING),
            (PartialDate(1990, 6, 30), PartialDate(1990, 7), Relation.BEFORE),
            (PartialDate(1990, 7), PartialDate(1990, 6, 30), Relation.AFTER),
        ],
    )
    def test_relation_to_names_how_the_periods_sit(self, first, second, expected):
        assert first.relation_to(second) is expected

    @pytest.mark.parametrize(
        "other",
        [datetime.date(1990, 6, 14), "1990-06-14", None],
        ids=["date", "str", "none"],
    )
    def test_relation_to_another_type_raises_type_error(self, other):
        with pytest.raises(TypeError):
            PartialDate(1990, 6, 14).relation_to(other)

    def test_before_and_after_mirror_each_other_over_every_pair(self):
        mirror = {
            Relation.BEFORE: Relation.AFTER,
            Relation.AFTER: Relation.BEFORE,
            Relation.OVERLAPPING: Relation.OVERLAPPING,
        }
        values = pair_sample()

        for left in values:
            for right in values:
                assert right.relation_to(left) is mirror[left.relation_to(right)]

    def test_each_relation_agrees_with_the_periods_over_every_pair(self):
        values = pair_sample()

        for left in values:
            for right in values:
                relation = left.relation_to(right)
                assert (relation is Relation.BEFORE) == (left.end < right.start)
                shares_a_day = left.start <= right.end and right.start <= left.end
                assert (relation is Relation.OVERLAPPING) == shares_a_day

    def test_before_agrees_with_the_coarser_precision_rule_over_every_pair(self):
        values = pair_sample()

        for left in values:
            for right in values:
                before = left.relation_to(right) is Relation.BEFORE
                assert before == is_earlier_at_the_coarser_precision(left, right)


class TestBuilding:
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
