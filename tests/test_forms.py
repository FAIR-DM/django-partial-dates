from html.parser import HTMLParser

import pytest
from django import forms

from partial_dates import PartialDate
from partial_dates.forms import PartialDateField

PARTS = ("year", "month", "day")


class Page(HTMLParser):
    """The selects, legend and tags found in a rendered form."""

    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.selects = {}
        self.legend = ""
        self.select = None
        self.option = None
        self.in_legend = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == "select":
            self.select = {"attrs": attrs, "options": []}
            self.selects[attrs["name"]] = self.select
        elif tag == "option":
            self.option = {
                "value": attrs["value"],
                "selected": "selected" in attrs,
                "label": "",
            }
            self.select["options"].append(self.option)
        elif tag == "legend":
            self.in_legend = True

    def handle_endtag(self, tag):
        if tag == "option":
            self.option = None
        elif tag == "legend":
            self.in_legend = False

    def handle_data(self, data):
        if self.option is not None:
            self.option["label"] += data
        elif self.in_legend:
            self.legend += data

    def values(self, part, name="when"):
        return [option["value"] for option in self.selects[f"{name}_{part}"]["options"]]

    def selected(self, part, name="when"):
        return [
            option["value"]
            for option in self.selects[f"{name}_{part}"]["options"]
            if option["selected"]
        ]


def make_form(**options):
    class WhenForm(forms.Form):
        when = PartialDateField(**options)

    return WhenForm


def posted(year="", month="", day=""):
    return {"when_year": year, "when_month": month, "when_day": day}


def render(form):
    return Page(form.as_div())


class TestEntering:
    @pytest.mark.parametrize("required", [True, False])
    @pytest.mark.parametrize(
        ("entry", "expected"),
        [
            (posted("1990"), PartialDate(1990)),
            (posted("1990", "6"), PartialDate(1990, 6)),
            (posted("1990", "6", "14"), PartialDate(1990, 6, 14)),
        ],
    )
    def test_the_parts_given_are_the_value_recorded(self, required, entry, expected):
        form = make_form(required=required)(entry)

        assert form.is_valid()
        assert form.cleaned_data["when"] == expected

    @pytest.mark.parametrize("required", [True, False])
    def test_every_select_offers_an_empty_choice(self, required):
        page = render(make_form(required=required)())

        for part in PARTS:
            assert "" in page.values(part)

    @pytest.mark.parametrize("required", [True, False])
    def test_a_blank_form_selects_no_part(self, required):
        page = render(make_form(required=required)())

        for part in PARTS:
            assert page.selected(part) == [""]

    def test_the_selects_come_in_the_order_year_month_day(self):
        page = render(make_form()())

        assert list(page.selects) == ["when_year", "when_month", "when_day"]

    def test_nothing_entered_on_an_optional_field_is_no_date(self):
        form = make_form(required=False)(posted())

        assert form.is_valid()
        assert form.cleaned_data["when"] is None

    def test_nothing_entered_on_a_required_field_is_refused_as_required(self):
        form = make_form(required=True)(posted())

        assert form.has_error("when", code="required")


class TestEditing:
    @pytest.mark.parametrize("as_text", [False, True])
    @pytest.mark.parametrize(
        ("initial", "selected"),
        [
            (PartialDate(1990), ["1990", "", ""]),
            (PartialDate(1990, 6), ["1990", "6", ""]),
            (PartialDate(1990, 6, 14), ["1990", "6", "14"]),
        ],
    )
    def test_a_stored_value_opens_with_exactly_its_parts_selected(
        self, initial, selected, as_text
    ):
        stored = initial.isoformat() if as_text else initial
        page = render(make_form()(initial={"when": stored}))

        assert [page.selected(part) for part in PARTS] == [
            [value] for value in selected
        ]

    @pytest.mark.parametrize(
        ("initial", "entry", "expected"),
        [
            (PartialDate(1990), posted("1990", "6"), PartialDate(1990, 6)),
            (PartialDate(1990), posted("1990", "6", "14"), PartialDate(1990, 6, 14)),
            (PartialDate(1990, 6), posted("1990", "6", "14"), PartialDate(1990, 6, 14)),
            (PartialDate(1990, 6, 14), posted("1990", "6"), PartialDate(1990, 6)),
            (PartialDate(1990, 6, 14), posted("1990"), PartialDate(1990)),
            (PartialDate(1990, 6), posted("1991", "6"), PartialDate(1991, 6)),
        ],
    )
    def test_adding_or_emptying_parts_changes_the_precision(
        self, initial, entry, expected
    ):
        form = make_form()(entry, initial={"when": initial})

        assert form.is_valid()
        assert form.cleaned_data["when"] == expected
        assert "when" in form.changed_data

    @pytest.mark.parametrize("as_text", [False, True])
    @pytest.mark.parametrize(
        ("initial", "entry"),
        [
            (PartialDate(1990), posted("1990")),
            (PartialDate(1990, 6), posted("1990", "6")),
            (PartialDate(1990, 6, 14), posted("1990", "6", "14")),
        ],
    )
    def test_an_untouched_form_reports_no_change_and_keeps_the_value(
        self, initial, entry, as_text
    ):
        stored = initial.isoformat() if as_text else initial
        form = make_form()(entry, initial={"when": stored})

        assert form.is_valid()
        assert form.changed_data == []
        assert form.cleaned_data["when"] == initial

    def test_a_year_outside_the_offered_years_is_selected_and_survives(self):
        initial = PartialDate(1850, 3)
        form = make_form()(initial={"when": initial})

        assert render(form).selected("year") == ["1850"]

        resubmitted = make_form()(posted("1850", "3"), initial={"when": initial})

        assert resubmitted.is_valid()
        assert resubmitted.changed_data == []
        assert resubmitted.cleaned_data["when"] == initial
