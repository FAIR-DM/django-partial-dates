import datetime

import django_filters
import pytest
from django.core.exceptions import ImproperlyConfigured

from partial_dates.fields import PartialDateField
from partial_dates.filters import PartialDateFilter
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
