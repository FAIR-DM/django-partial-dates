import datetime
import os
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import django_filters
import pytest
from django.core.exceptions import ImproperlyConfigured
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIRequestFactory

from partial_dates.fields import PartialDateField
from partial_dates.filters import PartialDateFilter, PartialDateRangeFilter
from partial_dates.partial_date import PartialDate
from tests.factories import NoteFactory, RecordFactory, SampleFactory
from tests.models import Record, Sample

TEXTS_IN_JUNE = ["1990-06", "1990-06-01", "1990-06-14"]
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


class TestAcrossARelation:
    @pytest.fixture
    def records(self, db):
        def make(*drafted):
            record = RecordFactory()
            for text in drafted:
                NoteFactory(record=record, drafted=text)
            return record

        return {
            "before and after": make("1989", "1992"),
            "inside": make("1990-09"),
            "inside twice": make("1990-09", "1991-01"),
            "inside and outside": make("1985", "1990-09"),
            "before": make("1985"),
            "after": make("1992-01"),
            "no note": make(),
        }

    @pytest.fixture
    def named(self, records):
        def names(queryset):
            by_pk = {record.pk: name for name, record in records.items()}
            return sorted(by_pk[record.pk] for record in queryset)

        return names

    @pytest.fixture
    def across(self, filterset):
        def apply(data, **kwargs):
            ranged = PartialDateRangeFilter(field_name="note__drafted", **kwargs)
            meta = type("Meta", (), {"model": Record, "fields": []})
            attrs = {"Meta": meta, "drafted": ranged}
            built = type("RecordFilter", (django_filters.FilterSet,), attrs)
            applied = built(data, queryset=Record.objects.all())
            assert applied.is_valid()
            return applied.qs

        return apply

    def test_both_bounds_apply_to_the_same_date(self, records, named, across):
        data = entered("1990", "1991", name="drafted")

        found = across(data, distinct=True)

        assert named(found) == ["inside", "inside and outside", "inside twice"]

    def test_a_record_with_one_date_either_side_of_the_range_is_not_found(
        self, records, named, across
    ):
        data = entered("1990", "1991", name="drafted")

        assert "before and after" not in named(across(data, distinct=True))

    def test_a_record_is_found_once_per_date_without_distinct(
        self, records, named, across
    ):
        data = entered("1990", "1992", name="drafted")

        found = named(across(data))

        assert found.count("inside twice") == 2
        assert found.count("inside") == 1

    def test_distinct_finds_a_record_once(self, records, named, across):
        data = entered("1990", "1992", name="drafted")

        found = named(across(data, distinct=True))

        assert found.count("inside twice") == 1

    def test_exclude_leaves_the_records_with_a_date_in_the_range_out(
        self, records, named, across
    ):
        data = entered("1990", "1991", name="drafted")

        found = across(data, exclude=True)

        assert named(found) == ["after", "before", "before and after", "no note"]


class SampleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    collected = serializers.CharField(allow_null=True)


class SampleFilter(django_filters.FilterSet):
    collected = PartialDateFilter()
    when = PartialDateRangeFilter(field_name="collected")

    class Meta:
        model = Sample
        fields = []


class SampleList(ListAPIView):
    queryset = Sample.objects.order_by("pk")
    serializer_class = SampleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SampleFilter
    authentication_classes = []
    permission_classes = []
    renderer_classes = [JSONRenderer]


class TestFilterBackend:
    @pytest.fixture
    def get(self):
        def request(**query):
            response = SampleList.as_view()(APIRequestFactory().get("/", query))
            response.render()
            return response

        return request

    @pytest.mark.parametrize(
        "text", ["1990-6", "1990-02-30", " 1990", "9" * 200, "1990\x00"]
    )
    @pytest.mark.parametrize("name", ["collected", "when_after", "when_before"])
    def test_text_that_is_not_a_partial_date_gives_a_400_naming_the_filter(
        self, grid, get, name, text
    ):
        response = get(**{name: text})

        assert response.status_code == 400
        assert response.data[name.split("_")[0]][0].code == "invalid"

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ({"collected": "1990-06"}, ["1990-06"]),
            ({"collected": "1990"}, ["1990"]),
            ({"when_after": "1990-06", "when_before": "1990-06"}, TEXTS_IN_JUNE),
        ],
    )
    def test_an_iso_form_gives_the_filtered_list(self, grid, get, query, expected):
        response = get(**query)

        assert response.status_code == 200
        assert [row["collected"] for row in response.data] == expected


SOURCE = """
import sys

sys.modules["rest_framework"] = None
import django

django.setup()
import django_filters

from partial_dates.filters import PartialDateFilter, PartialDateRangeFilter
from tests.models import Sample


class SampleFilter(django_filters.FilterSet):
    collected = PartialDateFilter()
    when = PartialDateRangeFilter(field_name="collected")

    class Meta:
        model = Sample
        fields = []


assert "collected" in SampleFilter.base_filters
"""


class TestWithoutRestFramework:
    def test_a_fresh_interpreter_with_it_blocked_builds_a_filter_set(self):
        env = {**os.environ, "DJANGO_SETTINGS_MODULE": "tests.settings"}
        root = Path(__file__).parent.parent

        result = subprocess.run(
            [sys.executable, "-c", SOURCE],
            env=env,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr


class Page(HTMLParser):
    """The selects and listed rows of a rendered filter page."""

    def __init__(self, html):
        super().__init__()
        self.selects = {}
        self.rows = []
        self._select = None
        self._row = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self._select = attrs["name"]
            self.selects[self._select] = {"values": [], "selected": ""}
        elif tag == "option" and self._select:
            self.selects[self._select]["values"].append(attrs["value"])
            if "selected" in attrs:
                self.selects[self._select]["selected"] = attrs["value"]
        elif tag == "li":
            self._row = ""

    def handle_endtag(self, tag):
        if tag == "select":
            self._select = None
        elif tag == "li":
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._row is not None:
            self._row += data


NAMES = ["collected", "when_after", "when_before"]


class TestListPage:
    @pytest.fixture
    def get(self, client):
        def request(query=None):
            response = client.get("/samples/", query or {})
            assert response.status_code == 200
            return response, Page(response.content.decode())

        return request

    @pytest.mark.parametrize("name", NAMES)
    @pytest.mark.parametrize("part", ["year", "month", "day"])
    def test_offers_a_select_for_each_part_with_an_empty_choice(
        self, grid, get, name, part
    ):
        page = get()[1]

        assert "" in page.selects[f"{name}_{part}"]["values"]

    def test_lists_every_record_including_one_holding_no_date(self, grid, get):
        page = get()[1]

        assert len(page.rows) == len(grid)
        assert "" in page.rows

    def test_a_range_lists_the_stretch_to_the_end_of_the_last_month(self, grid, get):
        page = get(entered(after="1990", before="1990-06", name="when"))[1]

        assert page.rows == [
            "1990",
            "1990-05",
            "1990-05-31",
            "1990-06",
            "1990-06-01",
            "1990-06-14",
        ]

    def test_a_range_given_by_selects_lists_the_same_stretch(self, grid, get):
        page = get(entered_by_parts(after="1990", before="1990-06", name="when"))[1]

        assert "1990-06-14" in page.rows
        assert "1990-07" not in page.rows

    @pytest.mark.parametrize(
        "query",
        [
            {},
            {"collected": ""},
            {"collected_year": "", "collected_month": "", "collected_day": ""},
            {"when_after": "", "when_before": ""},
            {
                "when_after_year": "",
                "when_after_month": "",
                "when_after_day": "",
                "when_before_year": "",
                "when_before_month": "",
                "when_before_day": "",
            },
        ],
    )
    def test_empty_parts_do_not_narrow(self, grid, get, query):
        page = get(query)[1]

        assert len(page.rows) == len(grid)

    @pytest.mark.parametrize(
        ("query", "code"),
        [
            ({"collected_day": "5"}, "incomplete"),
            (
                {
                    "collected_year": "1990",
                    "collected_month": "2",
                    "collected_day": "30",
                },
                "invalid",
            ),
            ({"when_after_year": "1990", "when_after_day": "5"}, "incomplete"),
            (
                {
                    "when_before_year": "1990",
                    "when_before_month": "2",
                    "when_before_day": "30",
                },
                "invalid",
            ),
        ],
    )
    def test_an_entry_that_makes_no_sense_is_reported_with_its_code(
        self, grid, get, query, code
    ):
        response, _page = get(query)

        errors = response.context["filter"].form.errors.as_data()
        assert [error.code for found in errors.values() for error in found] == [code]

    def test_the_address_of_a_narrowed_list_shows_the_same_rows_and_parts(
        self, grid, get
    ):
        query = entered_by_parts(after="1990-05", before="1990-06-01", name="when")
        first = get(query)[1]

        again = get(query)[1]

        assert again.rows == first.rows
        assert again.rows != [str(sample.collected or "") for sample in grid]
        assert again.selects["when_after_year"]["selected"] == "1990"
        assert again.selects["when_after_month"]["selected"] == "5"
        assert again.selects["when_before_day"]["selected"] == "1"

    def test_an_iso_address_shows_its_parts_selected(self, grid, get):
        page = get({"collected": "1990-06-14"})[1]

        assert page.selects["collected_year"]["selected"] == "1990"
        assert page.selects["collected_month"]["selected"] == "6"
        assert page.selects["collected_day"]["selected"] == "14"
        assert page.rows == ["1990-06-14"]

    @pytest.mark.parametrize(
        "query",
        [
            {"collected": "1990"},
            {"collected_year": "1990"},
            entered(after="0001", name="when"),
            entered(before="9999", name="when"),
        ],
    )
    def test_a_record_holding_no_date_is_left_out_once_narrowed(self, grid, get, query):
        page = get(query)[1]

        assert page.rows
        assert "" not in page.rows
