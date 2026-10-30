import datetime
import re

import pytest
from django.db.models import Count, F

from partial_dates import PartialDate
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

    def test_values_list_gives_the_year_of_every_date_and_none_for_no_date(self, grid):
        result = Sample.objects.order_by("pk").values_list("collected__year", flat=True)

        assert list(result) == [1990] * 7 + [1991, None]

    def test_values_and_annotate_give_a_whole_number(self, grid):
        values = Sample.objects.order_by("pk").values("collected__year")
        annotated = Sample.objects.annotate(year=F("collected__year")).order_by("pk")

        assert values[0] == {"collected__year": 1990}
        assert [sample.year for sample in annotated] == [1990] * 7 + [1991, None]

    def test_counts_grouped_by_year_include_every_row_with_a_date(self, grid):
        counts = (
            Sample.objects.values("collected__year")
            .annotate(total=Count("pk"))
            .order_by(F("collected__year").asc(nulls_last=True))
        )

        assert list(counts) == [
            {"collected__year": 1990, "total": 7},
            {"collected__year": 1991, "total": 1},
            {"collected__year": None, "total": 1},
        ]

    def test_order_by_year_is_numeric(self, db):
        for text in ["0990", "9999", "0001", "1990"]:
            SampleFactory(collected=text)

        result = Sample.objects.order_by("collected__year").values_list(
            "collected__year", flat=True
        )

        assert list(result) == [1, 990, 1990, 9999]


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

    def test_values_list_gives_the_month_and_none_where_it_is_unknown(self, grid):
        result = Sample.objects.order_by("pk").values_list(
            "collected__month", flat=True
        )

        assert list(result) == [None, 5, 5, 6, 6, 6, 7, None, None]

    def test_annotate_gives_a_whole_number(self, grid):
        annotated = Sample.objects.annotate(month=F("collected__month")).order_by("pk")

        assert [sample.month for sample in annotated][:4] == [None, 5, 5, 6]

    def test_counts_grouped_by_year_and_month_keep_a_year_out_of_every_month(
        self, grid
    ):
        counts = (
            Sample.objects.filter(collected__year=1990)
            .values("collected__year", "collected__month")
            .annotate(total=Count("pk"))
            .order_by("collected__month")
        )

        assert {row["collected__month"]: row["total"] for row in counts} == {
            None: 1,
            5: 2,
            6: 3,
            7: 1,
        }

    def test_order_by_month_is_numeric_with_unknown_months_last(self, db):
        for text in ["1990-10", "1990", "1990-02", "1990-09"]:
            SampleFactory(collected=text)

        result = Sample.objects.order_by(
            F("collected__month").asc(nulls_last=True)
        ).values_list("collected__month", flat=True)

        assert list(result) == [2, 9, 10, None]


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

    def test_values_list_gives_the_day_and_none_where_it_is_unknown(self, grid):
        result = Sample.objects.order_by("pk").values_list("collected__day", flat=True)

        assert list(result) == [None, None, 31, None, 1, 14, None, None, None]

    def test_annotate_gives_a_whole_number(self, grid):
        annotated = Sample.objects.annotate(day=F("collected__day")).order_by("pk")

        assert [sample.day for sample in annotated][2:6] == [31, None, 1, 14]

    def test_counts_grouped_by_year_month_and_day_keep_a_month_out_of_every_day(
        self, grid
    ):
        counts = (
            Sample.objects.filter(collected__year=1990, collected__month=6)
            .values("collected__year", "collected__month", "collected__day")
            .annotate(total=Count("pk"))
            .order_by(F("collected__day").asc(nulls_last=True))
        )

        assert [(row["collected__day"], row["total"]) for row in counts] == [
            (1, 1),
            (14, 1),
            (None, 1),
        ]

    def test_order_by_day_is_numeric_with_unknown_days_last(self, db):
        for text in ["1990-06-10", "1990-06", "1990-06-02", "1990-06-09"]:
            SampleFactory(collected=text)

        result = Sample.objects.order_by(
            F("collected__day").asc(nulls_last=True)
        ).values_list("collected__day", flat=True)

        assert list(result) == [2, 9, 10, None]


STARTS = [
    "0001",
    "1990",
    "1990-01",
    "1990-01-01",
    "1990-06",
    "1990-06-01",
    "1990-06-14",
    "2000-02-29",
    "9999-12-31",
]


@pytest.mark.django_db
class TestStart:
    @pytest.fixture
    def starts(self, db):
        return [SampleFactory(collected=text) for text in [*STARTS, None]]

    def test_values_list_gives_the_start_of_the_value_and_none_for_no_date(
        self, starts
    ):
        result = Sample.objects.order_by("pk").values_list(
            "collected__start", flat=True
        )

        assert list(result) == [
            *(PartialDate.fromisoformat(text).start for text in STARTS),
            None,
        ]

    def test_values_and_annotate_give_a_date(self, starts):
        values = Sample.objects.order_by("pk").values("collected__start")
        annotated = Sample.objects.annotate(first=F("collected__start")).order_by("pk")

        assert values[4] == {"collected__start": datetime.date(1990, 6, 1)}
        assert annotated[6].first == datetime.date(1990, 6, 14)

    def test_grouping_by_start_counts_dates_that_start_on_one_day(self, starts):
        counts = (
            Sample.objects.filter(collected__year=1990)
            .values("collected__start")
            .annotate(total=Count("pk"))
            .order_by("collected__start")
        )

        assert list(counts) == [
            {"collected__start": datetime.date(1990, 1, 1), "total": 3},
            {"collected__start": datetime.date(1990, 6, 1), "total": 2},
            {"collected__start": datetime.date(1990, 6, 14), "total": 1},
        ]

    def test_dates_that_share_a_start_stay_different_values(self, starts):
        result = Sample.objects.filter(collected__start=datetime.date(1990, 6, 1))

        assert sorted(str(sample.collected) for sample in result) == [
            "1990-06",
            "1990-06-01",
        ]

    @pytest.mark.parametrize(
        ("lookup", "expected"),
        [
            ("exact", ["1990-06-14"]),
            ("gt", ["2000-02-29", "9999-12-31"]),
            ("gte", ["1990-06-14", "2000-02-29", "9999-12-31"]),
            (
                "lt",
                ["0001", "1990", "1990-01", "1990-01-01", "1990-06", "1990-06-01"],
            ),
            (
                "lte",
                [
                    "0001",
                    "1990",
                    "1990-01",
                    "1990-01-01",
                    "1990-06",
                    "1990-06-01",
                    "1990-06-14",
                ],
            ),
        ],
    )
    def test_start_compares_with_a_real_date(self, starts, found, lookup, expected):
        result = found(
            Sample.objects.filter(
                **{f"collected__start__{lookup}": datetime.date(1990, 6, 14)}
            )
        )

        assert result == expected

    def test_start_range_includes_both_ends(self, starts, found):
        result = found(
            Sample.objects.filter(
                collected__start__range=(
                    datetime.date(1990, 6, 1),
                    datetime.date(1990, 6, 14),
                )
            )
        )

        assert result == ["1990-06", "1990-06-01", "1990-06-14"]

    def test_start_does_not_find_a_row_holding_no_date(self, starts, found):
        assert None not in found(
            Sample.objects.filter(collected__start__lte=datetime.date(9999, 12, 31))
        )

    def test_order_by_start_with_the_field_second_gives_a_stable_order(self, starts):
        result = Sample.objects.order_by(
            F("collected__start").asc(nulls_last=True), "collected"
        )

        assert [None if s.collected is None else str(s.collected) for s in result] == [
            "0001",
            "1990",
            "1990-01",
            "1990-01-01",
            "1990-06",
            "1990-06-01",
            "1990-06-14",
            "2000-02-29",
            "9999-12-31",
            None,
        ]

    @pytest.mark.parametrize("text", ["0001", "9999-12-31", "2000-02-29"])
    def test_start_is_exact_at_the_edges_of_the_calendar(self, db, text):
        SampleFactory(collected=text)

        result = Sample.objects.values_list("collected__start", flat=True).get()

        assert result == PartialDate.fromisoformat(text).start

    def test_year_month_day_and_start_equal_the_value_attributes(self, grid):
        rows = Sample.objects.exclude(collected=None).values_list(
            "collected",
            "collected__year",
            "collected__month",
            "collected__day",
            "collected__start",
        )

        for value, year, month, day, start in rows:
            assert (year, month, day, start) == (
                value.year,
                value.month,
                value.day,
                value.start,
            )


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


@pytest.mark.django_db
class TestQueryCount:
    @pytest.mark.parametrize(
        "lookup", [{"collected__year": 1990}, {"collected__month": 6}]
    )
    def test_a_part_filter_runs_one_query_for_one_row_and_for_several(
        self, django_assert_num_queries, lookup
    ):
        SampleFactory(collected="1990-06")

        with django_assert_num_queries(1):
            list(Sample.objects.filter(**lookup))

        SampleFactory.create_batch(4, collected="1990-06")

        with django_assert_num_queries(1):
            list(Sample.objects.filter(**lookup))
