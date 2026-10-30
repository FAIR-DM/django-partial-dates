import datetime

import django_filters
import pytest
from django.core.exceptions import ImproperlyConfigured

from partial_dates.fields import PartialDateField
from partial_dates.filters import PartialDateFilter, PartialDateRangeFilter
from partial_dates.partial_date import PartialDate
from tests.factories import SampleFactory
from tests.models import Sample

LOOKUPS = ["exact", "gt", "gte", "lt", "lte"]
BOUNDS = ["1990", "1990-06", "1990-06-14"]


@pytest.fixture
def filterset():
    def build(**filters):
        meta = type("Meta", (), {"model": Sample, "fields": []})
        attrs = {"Meta": meta, **filters}
        return type("SampleFilter", (django_filters.FilterSet,), attrs)

    return build


@pytest.fixture
def run(filterset):
    def apply(data, **filters):
        return filterset(**filters)(data, queryset=Sample.objects.all())

    return apply


@pytest.fixture
def refusal():
    def code(applied, name="collected"):
        assert not applied.is_valid()
        return applied.form.errors.as_data()[name][0].code

    return code


class TestPartialDateFilter:
    @pytest.mark.parametrize("lookup", LOOKUPS)
    @pytest.mark.parametrize("bound", BOUNDS)
    def test_finds_what_the_lookup_finds(self, grid, found, run, lookup, bound):
        bounded = PartialDateFilter(field_name="collected", lookup_expr=lookup)

        applied = run({"collected": bound}, collected=bounded)

        plain = Sample.objects.filter(**{f"collected__{lookup}": bound})
        assert found(applied.qs) == found(plain)
        assert None not in found(applied.qs)

    def test_exact_is_the_default_lookup(self, grid, found, run):
        applied = run({"collected": "1990-06"}, collected=PartialDateFilter())

        assert found(applied.qs) == ["1990-06"]

    @pytest.mark.parametrize(
        ("text", "parts"),
        [
            ("1990", {"collected_year": "1990"}),
            ("1990-06", {"collected_year": "1990", "collected_month": "6"}),
            (
                "1990-06-14",
                {
                    "collected_year": "1990",
                    "collected_month": "6",
                    "collected_day": "14",
                },
            ),
        ],
    )
    def test_text_and_select_parts_find_the_same_rows(
        self, grid, found, run, text, parts
    ):
        bounded = PartialDateFilter(lookup_expr="gte")

        by_text = run({"collected": text}, collected=bounded)
        by_parts = run(parts, collected=bounded)

        assert found(by_text.qs) == found(by_parts.qs)
        assert found(by_text.qs) != found(Sample.objects.all())

    def test_text_wins_when_both_arrive(self, grid, found, run):
        data = {"collected": "1990-06", "collected_year": "1991"}

        applied = run(data, collected=PartialDateFilter())

        assert found(applied.qs) == ["1990-06"]

    def test_an_empty_name_is_no_entry(self, grid, found, run):
        applied = run({"collected": ""}, collected=PartialDateFilter())

        assert applied.is_valid()
        assert found(applied.qs) == found(Sample.objects.all())

    def test_an_empty_name_leaves_the_parts_to_apply(self, grid, found, run):
        data = {"collected": "", "collected_year": "1990", "collected_month": "6"}

        applied = run(data, collected=PartialDateFilter())

        assert found(applied.qs) == ["1990-06"]

    @pytest.mark.parametrize(
        "text",
        [
            "1990-6",
            "1990-02-30",
            " 1990",
            "1990 ",
            "\uff11\uff19\uff19\uff10",
            "\u0661\u0669\u0669\u0660",
            "1990-06-14-01",
            "9" * 200,
            "1990\x00",
            "\x00",
        ],
    )
    def test_text_that_is_not_a_partial_date_is_refused(self, grid, run, refusal, text):
        applied = run({"collected": text}, collected=PartialDateFilter())

        assert refusal(applied) == "invalid"

    def test_an_entry_leaves_out_a_row_holding_no_date(self, grid, found, run):
        applied = run({"collected": "1991"}, collected=PartialDateFilter())

        assert None not in found(applied.qs)

    def test_no_entry_keeps_a_row_holding_no_date(self, grid, found, run):
        applied = run({}, collected=PartialDateFilter())

        assert None in found(applied.qs)


class TestPartFilters:
    @pytest.mark.parametrize("part", ["year", "month", "day"])
    @pytest.mark.parametrize("number", [1, 5, 6, 14, 1990, 1991])
    def test_each_finds_what_its_lookup_finds(self, grid, found, run, part, number):
        bounded = PartialDateFilter(lookup_expr=part)

        applied = run({"collected": str(number)}, collected=bounded)

        plain = Sample.objects.filter(**{f"collected__{part}": number})
        assert found(applied.qs) == found(plain)

    @pytest.mark.parametrize("part", ["year", "month", "day"])
    @pytest.mark.parametrize("comparison", ["exact", "gt", "gte", "lt", "lte"])
    def test_a_comparison_finds_what_its_lookup_finds(
        self, grid, found, run, part, comparison
    ):
        lookup = f"{part}__{comparison}"
        bounded = PartialDateFilter(lookup_expr=lookup)

        applied = run({"collected": "6"}, collected=bounded)

        plain = Sample.objects.filter(**{f"collected__{lookup}": 6})
        assert found(applied.qs) == found(plain)

    def test_a_month_leaves_out_a_year(self, grid, found, run):
        applied = run(
            {"collected": "6"}, collected=PartialDateFilter("collected", "month")
        )

        assert found(applied.qs) == ["1990-06", "1990-06-01", "1990-06-14"]

    def test_month_gte_works(self, grid, found, run):
        bounded = PartialDateFilter(lookup_expr="month__gte")

        applied = run({"collected": "6"}, collected=bounded)

        assert found(applied.qs) == ["1990-06", "1990-06-01", "1990-06-14", "1990-07"]

    @pytest.mark.parametrize(
        ("part", "number"),
        [
            ("year", 0),
            ("year", -1),
            ("year", 10000),
            ("month", 0),
            ("month", -1),
            ("month", 13),
            ("day", 0),
            ("day", -1),
            ("day", 32),
            ("month", 2**70),
        ],
    )
    def test_a_number_no_date_holds_finds_nothing(self, grid, found, run, part, number):
        bounded = PartialDateFilter(lookup_expr=part)

        applied = run({"collected": str(number)}, collected=bounded)

        assert applied.is_valid()
        assert found(applied.qs) == []

    @pytest.mark.parametrize("part", ["year", "month", "day"])
    @pytest.mark.parametrize("text", ["1990.5", "June"])
    def test_a_number_that_is_not_whole_is_refused(
        self, grid, run, refusal, part, text
    ):
        applied = run(
            {"collected": text}, collected=PartialDateFilter(lookup_expr=part)
        )

        assert refusal(applied) == "invalid"

    @pytest.mark.parametrize(
        "lookup",
        [
            "in",
            "range",
            "isnull",
            "contains",
            "startswith",
            "month__isnull",
            "year__in",
            "day__range",
            "year__month",
            "start__gte",
        ],
    )
    def test_a_lookup_outside_the_list_raises(self, lookup):
        with pytest.raises(ImproperlyConfigured):
            PartialDateFilter(lookup_expr=lookup)


class TestGeneratedFilters:
    @pytest.fixture
    def generated(self):
        def build(lookups):
            meta = type(
                "Meta",
                (),
                {
                    "model": Sample,
                    "fields": {"collected": lookups},
                    "filter_overrides": {
                        PartialDateField: {"filter_class": PartialDateFilter}
                    },
                },
            )
            return type("GeneratedFilter", (django_filters.FilterSet,), {"Meta": meta})

        return build

    @pytest.mark.parametrize("lookup", ["exact", "gt", "gte", "lt", "lte"])
    @pytest.mark.parametrize("bound", BOUNDS)
    def test_a_comparison_works(self, grid, found, generated, lookup, bound):
        filterset = generated([lookup])
        name = "collected" if lookup == "exact" else f"collected__{lookup}"

        applied = filterset({name: bound}, queryset=Sample.objects.all())

        plain = Sample.objects.filter(**{f"collected__{lookup}": bound})
        assert isinstance(filterset.base_filters[name], PartialDateFilter)
        assert found(applied.qs) == found(plain)

    @pytest.mark.parametrize(
        ("part", "number"), [("year", 1990), ("month", 6), ("day", 14)]
    )
    def test_a_part_works(self, grid, found, generated, part, number):
        filterset = generated([part])

        applied = filterset(
            {f"collected__{part}": str(number)}, queryset=Sample.objects.all()
        )

        plain = Sample.objects.filter(**{f"collected__{part}": number})
        assert found(applied.qs) == found(plain)
        assert found(applied.qs) != []

    @pytest.mark.parametrize("value", ["true", "false"])
    def test_isnull_works(self, grid, found, generated, value):
        filterset = generated(["isnull"])

        applied = filterset({"collected__isnull": value}, queryset=Sample.objects.all())

        plain = Sample.objects.filter(collected__isnull=value == "true")
        assert found(applied.qs) == found(plain)

    @pytest.mark.parametrize("lookup", ["in", "range"])
    def test_naming_a_list_lookup_raises_when_the_class_is_defined(
        self, generated, lookup
    ):
        with pytest.raises(ImproperlyConfigured):
            generated([lookup])


class TestOfferedYears:
    @pytest.fixture
    def offered(self, run):
        def years(**kwargs):
            applied = run({}, collected=PartialDateFilter(**kwargs))
            widget = applied.form.fields["collected"].widget
            context = widget.get_context("collected", None, {})
            select = context["widget"]["subwidgets"][0]
            return [
                str(option["value"])
                for _group, options, _index in select["optgroups"]
                for option in options
            ]

        return years

    def test_the_filter_offers_the_years_it_is_given(self, offered):
        assert offered(years=[2001, 1999, 2003]) == ["", "2001", "1999", "2003"]

    def test_the_filter_offers_the_default_years_with_none_given(self, offered):
        shown = offered()

        assert shown[1] == str(datetime.date.today().year)
        assert shown[-1] == "1900"


TEXTS = [
    "1990",
    "1990-05",
    "1990-05-31",
    "1990-06",
    "1990-06-14",
    "1990-07",
    "1991",
    "1991-03",
    "1991-03-14",
    "1991-03-15",
    "1991-03-31",
    "1991-04",
    "1991-06",
    "1991-06-14",
    "1991-12-31",
    "9999",
    "9999-12",
    "9999-12-31",
    None,
]


def entered(after=None, before=None, name="collected"):
    """Return the query string for a range, as ISO text."""
    return {
        f"{name}_{side}": bound
        for side, bound in (("after", after), ("before", before))
        if bound is not None
    }


def entered_by_parts(after=None, before=None, name="collected"):
    """Return the query string for a range, as the select parts."""
    data = {}
    for side, bound in (("after", after), ("before", before)):
        if bound is None:
            continue
        parts = PartialDate.fromisoformat(bound)
        data[f"{name}_{side}_year"] = str(parts.year)
        data[f"{name}_{side}_month"] = str(parts.month or "")
        data[f"{name}_{side}_day"] = str(parts.day or "")
    return data


class TestPartialDateRangeFilter:
    @pytest.fixture
    def calendar(self, db):
        return [SampleFactory(collected=text) for text in TEXTS]

    @pytest.fixture(params=[entered, entered_by_parts], ids=["text", "parts"])
    def query(self, request):
        return request.param

    @pytest.fixture
    def between(self, calendar, found, run, query):
        def rows(after=None, before=None, **filters):
            ranged = PartialDateRangeFilter(field_name="collected", **filters)
            applied = run(query(after, before), collected=ranged)
            assert applied.is_valid()
            return found(applied.qs)

        return rows

    @pytest.mark.parametrize(
        ("row", "stated"),
        [
            ("1990", False),
            ("1990-05-31", False),
            ("1990-06", True),
            ("1990-06-14", True),
            ("1991", True),
            ("1991-03", True),
            ("1991-03-15", True),
            ("1991-03-31", True),
            ("1991-04", False),
            (None, False),
        ],
    )
    def test_each_row_of_the_table_is_found_or_left_out(self, between, row, stated):
        assert (row in between("1990-06", "1991-03")) is stated

    def test_a_lower_bound_alone_applies(self, between):
        rows = between(after="1991-03-15")

        assert rows == [
            "1991-03-15",
            "1991-03-31",
            "1991-04",
            "1991-06",
            "1991-06-14",
            "1991-12-31",
            "9999",
            "9999-12",
            "9999-12-31",
        ]

    def test_an_upper_bound_alone_takes_in_the_whole_of_its_period(self, between):
        rows = between(before="1991-03")

        assert rows == TEXTS[:11]

    def test_no_bound_keeps_every_row(self, between):
        assert between() == TEXTS

    @pytest.mark.parametrize(
        ("after", "before", "expected"),
        [
            ("1991-04", "1991-03", []),
            ("1991-03-31", "1991-03", ["1991-03-31"]),
            ("1991-03-15", "1991-03", ["1991-03-15", "1991-03-31"]),
            ("1991-06", "1991", ["1991-06", "1991-06-14", "1991-12-31"]),
            ("1992", "1991", []),
            ("1991-03-14", "1991-03-14", ["1991-03-14"]),
        ],
    )
    def test_a_range_finds_nothing_only_after_the_last_day_of_its_period(
        self, between, after, before, expected
    ):
        assert between(after, before) == expected

    @pytest.mark.parametrize("bound", ["1990", "1990-06", "1990-06-14"])
    def test_a_lower_bound_of_each_precision_finds_what_gte_finds(
        self, calendar, found, between, bound
    ):
        assert between(after=bound) == found(
            Sample.objects.filter(collected__gte=bound)
        )

    @pytest.mark.parametrize("bound", ["1990", "1990-06", "1990-06-14"])
    def test_an_upper_bound_of_each_precision_finds_what_lte_the_last_day_finds(
        self, calendar, found, between, bound
    ):
        last = PartialDate.fromisoformat(bound).end.isoformat()

        assert between(before=bound) == found(
            Sample.objects.filter(collected__lte=last)
        )

    @pytest.mark.parametrize("after", ["1990", "1990-06", "1990-06-14"])
    @pytest.mark.parametrize("before", ["1990", "1990-06", "1990-06-14", "1991"])
    def test_both_bounds_find_what_gte_and_lte_find_together(
        self, calendar, found, between, after, before
    ):
        last = PartialDate.fromisoformat(before).end.isoformat()
        plain = Sample.objects.filter(collected__gte=after, collected__lte=last)

        assert between(after, before) == found(plain)

    @pytest.mark.parametrize(
        ("after", "before", "expected"),
        [
            ("9999", None, ["9999", "9999-12", "9999-12-31"]),
            ("9999-12", None, ["9999-12", "9999-12-31"]),
            ("9999-12", "9999-12", ["9999-12", "9999-12-31"]),
            ("9999", "9999", ["9999", "9999-12", "9999-12-31"]),
            ("9999-12-31", "9999-12", ["9999-12-31"]),
            ("1991-12", "9999", TEXTS[14:-1]),
        ],
    )
    def test_the_latest_bounds_work_as_any_other(
        self, between, after, before, expected
    ):
        assert between(after, before) == expected

    @pytest.mark.parametrize("side", ["after", "before"])
    @pytest.mark.parametrize("text", ["1990-6", "1990-02-30", " 1990", "1990\x00"])
    def test_a_text_bound_that_is_not_a_partial_date_is_refused(
        self, calendar, run, refusal, side, text
    ):
        data = {f"collected_{side}": text}

        applied = run(data, collected=PartialDateRangeFilter())

        assert refusal(applied) == "invalid"

    @pytest.mark.parametrize("side", ["after", "before"])
    def test_a_bound_of_select_parts_that_does_not_exist_is_refused(
        self, calendar, run, refusal, side
    ):
        data = {
            f"collected_{side}_year": "1990",
            f"collected_{side}_month": "2",
            f"collected_{side}_day": "30",
        }

        applied = run(data, collected=PartialDateRangeFilter())

        assert refusal(applied) == "invalid"

    @pytest.mark.parametrize("side", ["after", "before"])
    def test_a_day_without_a_month_is_refused(self, calendar, run, refusal, side):
        data = {f"collected_{side}_year": "1990", f"collected_{side}_day": "5"}

        applied = run(data, collected=PartialDateRangeFilter())

        assert refusal(applied) == "incomplete"

    def test_a_refused_bound_is_not_taken_for_no_entry(self, calendar, run):
        data = entered(after="1990-06", before="1991-3")

        applied = run(data, collected=PartialDateRangeFilter())

        assert not applied.is_valid()

    def test_text_wins_over_select_parts_of_the_same_bound(self, calendar, found, run):
        data = {**entered(after="1991-04"), "collected_after_year": "1990"}

        applied = run(data, collected=PartialDateRangeFilter())

        assert found(applied.qs) == found(
            Sample.objects.filter(collected__gte="1991-04")
        )

    @pytest.fixture
    def offered(self, run):
        def years(**kwargs):
            applied = run({}, collected=PartialDateRangeFilter(**kwargs))
            widget = applied.form.fields["collected"].widget
            context = widget.get_context("collected", None, {})
            return [
                [
                    str(option["value"])
                    for _group, options, _index in bound["subwidgets"][0]["optgroups"]
                    for option in options
                ]
                for bound in context["widget"]["subwidgets"]
            ]

        return years

    def test_the_years_it_is_given_reach_both_bounds(self, offered):
        both = ["", "2001", "1999", "2003"]

        assert offered(years=[2001, 1999, 2003]) == [both, both]
