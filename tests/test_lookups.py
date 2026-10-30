import re

import pytest
from django.db.models import F

from tests.factories import EventFactory, RecordFactory, SampleFactory
from tests.models import Event, Record, Sample


@pytest.mark.django_db
class TestYear:
    def test_year_finds_dates_at_every_precision(self, grid, found):
        result = found(Sample.objects.filter(collected__year=1990))

        assert result == [
            "1990",
            "1990-05",
            "1990-05-31",
            "1990-06",
            "1990-06-01",
            "1990-06-14",
            "1990-07",
        ]

    def test_year_does_not_find_a_row_holding_no_date(self, grid, found):
        assert None not in found(Sample.objects.filter(collected__year=1990))

    @pytest.mark.parametrize("year", [1, 990, 9999])
    def test_year_finds_early_and_late_years_by_number(self, year, found):
        SampleFactory(collected="0001")
        SampleFactory(collected="0990")
        SampleFactory(collected="9999-12-31")

        result = found(Sample.objects.filter(collected__year=year))

        assert result == [{1: "0001", 990: "0990", 9999: "9999-12-31"}[year]]

    @pytest.mark.parametrize("year", [0, 10000])
    def test_a_year_no_date_can_hold_finds_nothing(self, grid, year):
        assert not Sample.objects.filter(collected__year=year).exists()

    def test_year_compares_as_a_number(self, grid, found):
        result = found(Sample.objects.filter(collected__year__gte=1991))

        assert result == ["1991"]

    def test_year_in_finds_any_listed_year(self, grid, found):
        result = found(Sample.objects.filter(collected__year__in=[1991, 2000]))

        assert result == ["1991"]

    def test_year_range_includes_both_ends(self, grid, found):
        result = found(Sample.objects.filter(collected__year__range=(1991, 2000)))

        assert result == ["1991"]

    def test_year_isnull_is_true_only_for_a_row_holding_no_date(self, grid, found):
        assert found(Sample.objects.filter(collected__year__isnull=True)) == [None]

    def test_exclude_year_returns_other_years_and_the_row_holding_no_date(
        self, grid, found
    ):
        result = found(Sample.objects.exclude(collected__year=1990))

        assert result == ["1991", None]

    def test_exclude_year_on_a_required_field_returns_other_years(self, db):
        EventFactory(occurred="1990-06")
        other = EventFactory(occurred="1991")

        assert list(Event.objects.exclude(occurred__year=1990)) == [other]

    def test_two_fields_on_one_model_are_filtered_on_their_own(self, db):
        record = RecordFactory(date="1990-06", other="1991")

        assert list(Record.objects.filter(date__year=1990)) == [record]
        assert not Record.objects.filter(other__year=1990).exists()


@pytest.mark.django_db
class TestMonth:
    def test_month_finds_dates_at_month_and_day_precision(self, grid, found):
        result = found(Sample.objects.filter(collected__month=6))

        assert result == ["1990-06", "1990-06-01", "1990-06-14"]

    def test_month_does_not_find_a_date_whose_month_is_unknown(self, grid, found):
        result = found(Sample.objects.filter(collected__month=6))

        assert "1990" not in result

    def test_month_compares_as_a_number(self, grid, found):
        result = found(Sample.objects.filter(collected__month__gte=6))

        assert result == ["1990-06", "1990-06-01", "1990-06-14", "1990-07"]

    def test_month_in_finds_any_listed_month(self, grid, found):
        result = found(Sample.objects.filter(collected__month__in=[5, 7]))

        assert result == ["1990-05", "1990-05-31", "1990-07"]

    def test_month_isnull_selects_dates_at_year_precision_and_no_date(
        self, grid, found
    ):
        result = found(Sample.objects.filter(collected__month__isnull=True))

        assert result == ["1990", "1991", None]

    def test_month_isnull_false_selects_dates_at_month_and_day_precision(
        self, grid, found
    ):
        result = found(Sample.objects.filter(collected__month__isnull=False))

        assert result == [
            "1990-05",
            "1990-05-31",
            "1990-06",
            "1990-06-01",
            "1990-06-14",
            "1990-07",
        ]

    def test_exclude_month_leaves_out_a_date_whose_month_is_unknown(self, grid, found):
        result = found(Sample.objects.exclude(collected__month=6))

        assert "1990" not in result
        assert "1991" not in result

    def test_exclude_month_returns_other_months_and_the_row_holding_no_date(
        self, grid, found
    ):
        result = found(Sample.objects.exclude(collected__month=6))

        assert result == ["1990-05", "1990-05-31", "1990-07", None]

    def test_exclude_month_on_a_required_field_leaves_out_year_precision(self, db):
        EventFactory(occurred="1990")
        EventFactory(occurred="1990-06")
        other = EventFactory(occurred="1990-07")

        assert list(Event.objects.exclude(occurred__month=6)) == [other]

    @pytest.mark.parametrize("month", [0, 13])
    def test_a_month_no_date_can_hold_finds_nothing(self, grid, month):
        assert not Sample.objects.filter(collected__month=month).exists()

    def test_two_fields_on_one_model_are_filtered_on_their_own(self, db):
        record = RecordFactory(date="1990-06", other="1991-01-14")

        assert list(Record.objects.filter(date__month=6)) == [record]
        assert not Record.objects.filter(other__month=6).exists()


@pytest.mark.django_db
class TestDay:
    def test_day_finds_only_dates_at_day_precision(self, grid, found):
        result = found(Sample.objects.filter(collected__day=14))

        assert result == ["1990-06-14"]

    def test_day_one_finds_the_first_of_the_month_and_not_the_month(self, grid, found):
        result = found(Sample.objects.filter(collected__day=1))

        assert result == ["1990-06-01"]

    def test_day_isnull_selects_dates_without_a_day_and_no_date(self, grid, found):
        result = found(Sample.objects.filter(collected__day__isnull=True))

        assert result == ["1990", "1990-05", "1990-06", "1990-07", "1991", None]

    def test_day_isnull_false_selects_dates_at_day_precision(self, grid, found):
        result = found(Sample.objects.filter(collected__day__isnull=False))

        assert result == ["1990-05-31", "1990-06-01", "1990-06-14"]

    def test_exclude_day_leaves_out_dates_whose_day_is_unknown(self, grid, found):
        result = found(Sample.objects.exclude(collected__day=14))

        assert result == ["1990-05-31", "1990-06-01", None]

    def test_exclude_day_on_a_required_field_leaves_out_unknown_days(self, db):
        EventFactory(occurred="1990-06")
        EventFactory(occurred="1990-06-14")
        other = EventFactory(occurred="1990-06-15")

        assert list(Event.objects.exclude(occurred__day=14)) == [other]

    @pytest.mark.parametrize("day", [0, 32])
    def test_a_day_no_date_can_hold_finds_nothing(self, grid, day):
        assert not Sample.objects.filter(collected__day=day).exists()

    def test_two_fields_on_one_model_are_filtered_on_their_own(self, db):
        record = RecordFactory(date="1990-06-14", other="1991-06")

        assert list(Record.objects.filter(date__day=14)) == [record]
        assert not Record.objects.filter(other__day=14).exists()


NAMES_AN_INDEX = re.compile(r"\bindex\b", re.IGNORECASE)


@pytest.mark.django_db
class TestYearIndex:
    def test_year_equality_uses_the_index(self, grid, query_plan):
        plan = query_plan(Sample.objects.filter(collected__year=1990))

        assert NAMES_AN_INDEX.search(plan)

    def test_month_equality_reads_the_whole_table(self, grid, query_plan):
        plan = query_plan(Sample.objects.filter(collected__month=6))

        assert not NAMES_AN_INDEX.search(plan)

    def test_year_still_compares_with_another_year(self, db):
        same = RecordFactory(date="1990-06", other="1990")
        RecordFactory(date="1990", other="1991")

        found = Record.objects.filter(date__year=F("other__year"))

        assert list(found) == [same]
