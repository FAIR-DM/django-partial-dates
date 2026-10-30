import itertools
from html.parser import HTMLParser

import pytest
from django import forms
from django.utils import translation
from django.utils.dates import MONTHS

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


class TestRefusing:
    @pytest.mark.parametrize("stored", [None, PartialDate(1990, 6, 14)])
    def test_a_day_with_no_month_is_incomplete_and_never_dropped(self, stored):
        form = make_form()(posted("1990", "", "14"), initial={"when": stored})

        assert form.has_error("when", code="incomplete")
        assert "when" not in form.cleaned_data

    @pytest.mark.parametrize(
        "entry", [posted("", "6"), posted("", "", "14"), posted("", "6", "14")]
    )
    def test_a_part_with_no_year_is_incomplete(self, entry):
        form = make_form()(entry)

        assert form.has_error("when", code="incomplete")

    @pytest.mark.parametrize(
        "entry",
        [
            posted("1990", "2", "30"),
            posted("1900", "2", "29"),
            posted("1990", "13"),
            posted("1990", "0"),
            posted("1990", "0", "5"),
            posted("1990", "6", "0"),
            posted("1990", "6", "32"),
            posted("1990", "x"),
            posted("1990", "6", "x"),
            posted("x"),
            posted("0"),
            posted("-5"),
            posted("10000"),
            posted("9" * 5000),
        ],
    )
    def test_a_date_that_does_not_exist_or_cannot_be_read_is_invalid(self, entry):
        form = make_form()(entry)

        assert form.has_error("when", code="invalid")
        assert "when" not in form.cleaned_data

    def test_the_29th_of_february_is_accepted_in_a_leap_year(self):
        form = make_form()(posted("2000", "2", "29"))

        assert form.is_valid()
        assert form.cleaned_data["when"] == PartialDate(2000, 2, 29)

    @pytest.mark.parametrize(
        "entry",
        [
            posted("1990", "", "14"),
            posted("1990", "2", "30"),
            posted("1850", "2", "31"),
            posted("", "6", "14"),
        ],
    )
    def test_a_refused_entry_comes_back_with_each_submitted_part_selected(self, entry):
        form = make_form()(entry)

        page = render(form)

        assert not form.is_valid()
        for part in PARTS:
            assert page.selected(part) == [entry[f"when_{part}"]]

    @pytest.mark.parametrize("year", ["1990", "1850", "2500"])
    def test_a_year_is_listed_once_however_it_came_to_be_shown(self, year):
        page = render(make_form()(posted(year, "", "14")))

        assert page.values("year").count(year) == 1

    @pytest.mark.parametrize("year", ["0", "x", "-5", "10000", "9" * 5000])
    def test_a_year_no_date_can_have_is_never_offered(self, year):
        page = render(make_form()(posted(year)))

        assert year not in page.values("year")


class TestEveryCombination:
    @pytest.mark.parametrize(
        ("year", "month", "day"),
        list(
            itertools.product(
                ["", "1990", "0", "x"],
                ["", "6", "2", "13", "0", "x"],
                ["", "14", "30", "29", "x"],
            )
        ),
    )
    def test_an_entry_is_stored_with_exactly_its_parts_or_refused_with_a_code(
        self, year, month, day
    ):
        form = make_form(required=False)(posted(year, month, day))

        if form.is_valid():
            value = form.cleaned_data["when"]
            if not (year or month or day):
                assert value is None
            else:
                assert value.year == int(year)
                assert value.month == (int(month) if month else None)
                assert value.day == (int(day) if day else None)
        else:
            codes = {error.code for error in form.errors.as_data()["when"]}
            assert codes
            assert codes <= {"required", "incomplete", "invalid"}


class TestAcrossLanguages:
    @pytest.mark.parametrize("language", ["en", "de", "ja"])
    def test_the_selects_keep_the_order_year_month_day(self, language):
        form = make_form()()

        with translation.override(language):
            page = render(form)

        assert list(page.selects) == ["when_year", "when_month", "when_day"]

    @pytest.mark.parametrize("language", ["en", "de", "ja"])
    def test_each_month_is_named_in_the_active_language(self, language):
        form = make_form()()

        with translation.override(language):
            page = render(form)
            named = {number: str(name) for number, name in MONTHS.items()}

        labels = {
            int(option["value"]): option["label"]
            for option in page.selects["when_month"]["options"]
            if option["value"]
        }
        assert labels == named

    def test_the_month_names_follow_the_language(self):
        form = make_form()()

        with translation.override("en"):
            english = render(form).selects["when_month"]["options"]
        with translation.override("de"):
            german = render(form).selects["when_month"]["options"]

        assert english[3]["label"] != german[3]["label"]


class TestAssistiveUse:
    def test_each_select_has_a_name_of_its_own(self):
        page = render(make_form()())

        names = [select["attrs"].get("aria-label") for select in page.selects.values()]
        assert all(names)
        assert len(set(names)) == len(PARTS)

    def test_the_year_is_the_first_select(self):
        page = render(make_form()())

        assert next(iter(page.selects)) == "when_year"

    def test_the_field_is_a_fieldset_led_by_its_label_as_the_legend(self):
        form = make_form()()

        page = render(form)

        assert "fieldset" in page.tags
        assert page.legend.strip().startswith(str(form["when"].label))


class TestNoScript:
    def test_the_form_needs_no_media(self):
        assert str(make_form()().media) == ""

    def test_the_render_holds_no_script(self):
        page = render(make_form()())

        assert "script" not in page.tags
