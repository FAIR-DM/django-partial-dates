"""Tests for the partial date value."""

import calendar
import dataclasses
import datetime
import io
import json
import operator

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.template import engines
from django.test import override_settings
from django.utils import translation
from django.utils.formats import date_format, number_format, reset_format_cache

from partial_dates import PartialDate, Precision, Relation
from tests.factories import RecordFactory
from tests.models import Record


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


class TestDisplayForm:
    @pytest.mark.parametrize(
        ("language", "year", "month", "day"),
        [
            ("en", "1990", "June 1990", "June 14, 1990"),
            ("de", "1990", "Juni 1990", "14. Juni 1990"),
            ("ja", "1990", "1990年6月", "1990年6月14日"),
        ],
    )
    def test_each_precision_reads_in_the_active_language(
        self, language, year, month, day
    ):
        with translation.override(language):
            assert PartialDate(1990).display_form() == year
            assert PartialDate(1990, 6).display_form() == month
            assert PartialDate(1990, 6, 14).display_form() == day

    def test_one_value_reads_in_the_language_active_when_it_is_shown(self):
        value = PartialDate(1990, 6, 14)

        with translation.override("en"):
            english = value.display_form()
        with translation.override("de"):
            german = value.display_form()

        assert english != german
        with translation.override("en"):
            assert value.display_form() == english

    @override_settings(
        USE_THOUSAND_SEPARATOR=True, THOUSAND_SEPARATOR=",", NUMBER_GROUPING=3
    )
    @pytest.mark.parametrize("value", [PartialDate(1990), PartialDate(1990, 6)])
    def test_the_year_carries_no_thousands_separator(self, value):
        with translation.override("en"):
            assert number_format(1990) == "1,990"
            assert "1990" in value.display_form()

    @override_settings(
        USE_THOUSAND_SEPARATOR=True, THOUSAND_SEPARATOR=",", NUMBER_GROUPING=3
    )
    def test_a_full_date_carries_no_thousands_separator(self):
        with translation.override("en"):
            assert "1990" in PartialDate(1990, 6, 14).display_form()

    @pytest.mark.parametrize("language", ["en", "de", "ja"])
    def test_a_year_below_a_thousand_reads_the_same_at_every_precision(self, language):
        with translation.override(language):
            texts = [
                PartialDate(990, month, day).display_form()
                for month, day in [(None, None), (6, None), (6, 14)]
            ]
            year = PartialDate(990).display_form()

        assert year == "0990"
        assert all(year in text for text in texts)

    @pytest.mark.parametrize(
        "value", [PartialDate(1990), PartialDate(1990, 1), PartialDate(1990, 1, 1)]
    )
    def test_a_time_zone_far_from_utc_changes_nothing(self, value):
        with translation.override("en"):
            expected = value.display_form()
            with override_settings(TIME_ZONE="Pacific/Kiritimati"):
                assert value.display_form() == expected
            with override_settings(TIME_ZONE="Pacific/Pago_Pago"):
                assert value.display_form() == expected

    @override_settings(USE_I18N=False, LANGUAGE_CODE="de")
    def test_a_site_without_translation_reads_in_its_language_code(self):
        assert PartialDate(1990, 6, 14).display_form() == "14. Juni 1990"
        assert PartialDate(1990, 6).display_form() == "Juni 1990"

    @pytest.mark.parametrize(
        ("value", "name"),
        [
            (PartialDate(1990, 6), "YEAR_MONTH_FORMAT"),
            (PartialDate(1990, 6, 14), "DATE_FORMAT"),
        ],
    )
    def test_a_language_without_formats_reads_as_django_writes_it(self, value, name):
        with translation.override("xx"):
            assert value.display_form() == date_format(value.start, name)

    @pytest.mark.parametrize(
        "value", [PartialDate(1990), PartialDate(1990, 6), PartialDate(1990, 6, 14)]
    )
    @pytest.mark.parametrize("language", ["en", "de", "ja"])
    def test_it_equals_what_the_filter_renders_with_no_request(self, language, value):
        template = engines["django"].from_string(
            "{% load partial_dates %}{{ value|partial_date }}"
        )

        with translation.override(language):
            rendered = template.render({"value": value})

            assert value.display_form() == rendered

    @pytest.fixture
    def project_formats(self):
        reset_format_cache()
        with override_settings(FORMAT_MODULE_PATH=["tests.formats"]):
            yield
        reset_format_cache()

    def test_a_project_format_module_sets_the_month_and_the_day_format(
        self, project_formats
    ):
        with translation.override("en"):
            assert PartialDate(1990, 6).display_form() == "1990/06"
            assert PartialDate(1990, 6, 14).display_form() == "<14>/06/1990"


class TestDisplayFormNamesOnlyRecordedParts:
    @pytest.mark.parametrize("language", [code for code, _ in settings.LANGUAGES])
    def test_a_year_reads_the_same_on_its_first_and_its_last_day(self, language):
        with translation.override(language):
            text = PartialDate(1990).display_form()

            assert text == date_format(datetime.date(1990, 1, 1), "Y")
            assert text == date_format(datetime.date(1990, 12, 31), "Y")

    @pytest.mark.parametrize("language", [code for code, _ in settings.LANGUAGES])
    def test_a_month_reads_the_same_on_its_first_and_its_last_day(self, language):
        with translation.override(language):
            text = PartialDate(1990, 6).display_form()

            assert text == date_format(datetime.date(1990, 6, 1), "YEAR_MONTH_FORMAT")
            assert text == date_format(datetime.date(1990, 6, 30), "YEAR_MONTH_FORMAT")


class TestISOFormStays:
    @pytest.mark.parametrize("language", ["de", "ja"])
    @pytest.mark.parametrize(
        ("value", "text"),
        [
            (PartialDate(1990), "1990"),
            (PartialDate(1990, 6), "1990-06"),
            (PartialDate(1990, 6, 14), "1990-06-14"),
        ],
    )
    def test_str_isoformat_and_a_bare_template_variable_give_the_iso_form(
        self, language, value, text
    ):
        template = engines["django"].from_string("{{ value }}")

        with translation.override(language):
            assert str(value) == text
            assert value.isoformat() == text
            assert template.render({"value": value}) == text

    @pytest.mark.django_db
    def test_what_is_stored_and_dumped_does_not_depend_on_the_language(self):
        def stored_and_dumped():
            out = io.StringIO()
            call_command("dumpdata", "tests.Record", stdout=out)
            with connection.cursor() as cursor:
                cursor.execute("SELECT date FROM tests_record")
                return cursor.fetchall(), out.getvalue()

        RecordFactory(date="1990-06")
        with translation.override("en"):
            english = stored_and_dumped()
        with translation.override("de"):
            record = Record.objects.get()
            record.save()
            german = stored_and_dumped()

        assert german == english
        assert english[0] == [("1990-06",)]
        assert json.loads(english[1])[0]["fields"]["date"] == "1990-06"
