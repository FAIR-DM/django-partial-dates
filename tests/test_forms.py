import datetime
import itertools
import os
import subprocess
import sys
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from django import forms
from django.forms import formset_factory
from django.utils import translation
from django.utils.dates import MONTHS

from partial_dates import PartialDate
from partial_dates import forms as partial_forms
from partial_dates.forms import PartialDateField, PartialDateWidget

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


def posted(year="", month="", day="", name="when"):
    return {f"{name}_year": year, f"{name}_month": month, f"{name}_day": day}


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


def make_form_with(**fields):
    return type("ManyForm", (forms.Form,), fields)


def years_widget(years):
    return PartialDateField(widget=PartialDateWidget(years=years))


class TestDeclaring:
    @pytest.mark.parametrize("required", [True, False])
    def test_a_form_with_no_model_cleans_to_a_partial_date(self, required):
        form = make_form(required=required)(posted("1990", "6"))

        assert form.is_valid()
        assert isinstance(form.cleaned_data["when"], PartialDate)

    def test_a_form_with_no_model_cleans_nothing_to_none(self):
        form = make_form(required=False)(posted())

        assert form.is_valid()
        assert form.cleaned_data["when"] is None


class TestOfferedYears:
    def test_the_default_runs_from_this_year_to_1900_newest_first(self):
        page = render(make_form()())

        this_year = datetime.date.today().year
        expected = [str(year) for year in range(this_year, 1899, -1)]
        assert page.values("year") == ["", *expected]

    def test_named_years_are_the_years_one_field_offers_and_others_keep_theirs(self):
        form = make_form_with(
            named=years_widget([2001, 2000]), other=PartialDateField()
        )

        page = render(form())

        assert page.values("year", "named") == ["", "2001", "2000"]
        assert page.values("year", "other")[:2] == [
            "",
            str(datetime.date.today().year),
        ]

    def test_a_year_outside_the_named_years_is_still_accepted(self):
        form = make_form_with(when=years_widget([2001, 2000]))(posted("1850", "3"))

        assert form.is_valid()
        assert form.cleaned_data["when"] == PartialDate(1850, 3)

    def test_the_default_list_follows_the_clock_on_a_form_class_already_defined(
        self, monkeypatch
    ):
        form_class = make_form()

        class Later(datetime.date):
            @classmethod
            def today(cls):
                return cls(2100, 1, 1)

        monkeypatch.setattr(partial_forms, "datetime", SimpleNamespace(date=Later))

        assert render(form_class()).values("year")[:2] == ["", "2100"]

    def test_a_generator_of_years_lists_them_on_a_second_render(self):
        form_class = make_form_with(when=years_widget(y for y in (2002, 2001)))

        first = render(form_class()).values("year")
        second = render(form_class()).values("year")

        assert first == second == ["", "2002", "2001"]


class TestSeveralFields:
    def test_two_fields_on_one_form_are_read_and_validated_on_their_own(self):
        form = make_form_with(start=PartialDateField(), end=PartialDateField())(
            {**posted("1990", name="start"), **posted("1991", "2", "30", name="end")}
        )

        assert not form.is_valid()
        assert form.cleaned_data["start"] == PartialDate(1990)
        assert form.has_error("end", code="invalid")
        assert not form.has_error("start")

    def test_a_form_with_a_prefix_reads_its_prefixed_names(self):
        form = make_form()({"p-when_year": "1990", "p-when_month": "6"}, prefix="p")

        page = render(form)

        assert form.is_valid()
        assert form.cleaned_data["when"] == PartialDate(1990, 6)
        assert list(page.selects) == ["p-when_year", "p-when_month", "p-when_day"]

    def test_each_form_of_a_formset_is_read_and_validated_on_its_own(self):
        formset = formset_factory(make_form(), extra=0)(
            {
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-0-when_year": "1990",
                "form-1-when_year": "1991",
                "form-1-when_month": "",
                "form-1-when_day": "14",
            }
        )

        assert not formset.is_valid()
        assert formset.forms[0].cleaned_data["when"] == PartialDate(1990)
        assert formset.forms[1].has_error("when", code="incomplete")


class TestNothingConfigured:
    def test_a_fresh_interpreter_with_no_apps_or_templates_renders_and_cleans(self):
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        code = "\n".join(
            [
                "import django",
                "from django.conf import settings",
                "settings.configure(INSTALLED_APPS=[], TEMPLATES=[])",
                "django.setup()",
                "from django import forms",
                "from partial_dates import PartialDate",
                "from partial_dates.forms import PartialDateField",
                "class F(forms.Form):",
                "    when = PartialDateField()",
                "assert 'name=\"when_year\"' in F().as_div()",
                "form = F({'when_year': '1990', 'when_month': '6'})",
                "assert form.is_valid()",
                "assert form.cleaned_data['when'] == PartialDate(1990, 6)",
            ]
        )

        result = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr


class TestEdgeCases:
    def test_a_year_below_1000_is_recorded_with_four_digits(self):
        form = make_form_with(when=years_widget([990, 1990]))(posted("990"))

        assert form.is_valid()
        assert form.cleaned_data["when"].isoformat() == "0990"

    def test_a_stored_year_below_1000_opens_selected(self):
        form = make_form_with(when=years_widget([990, 1990]))(
            initial={"when": PartialDate(990)}
        )

        assert render(form).selected("year") == ["990"]

    @pytest.mark.parametrize(
        ("entry", "expected"),
        [
            ({"when_year": "1990"}, PartialDate(1990)),
            ({"when_year": "1990", "when_month": "6"}, PartialDate(1990, 6)),
            ({}, None),
        ],
    )
    def test_a_part_left_out_of_the_submission_reads_as_empty(self, entry, expected):
        form = make_form(required=False)(entry)

        assert form.is_valid()
        assert form.cleaned_data["when"] == expected

    @pytest.mark.parametrize(
        "hand_edited", ["", "garbage", "1990-13-45", "1990-6", "9" * 5000]
    )
    def test_a_hand_edited_hidden_initial_on_an_extra_formset_form_raises_nothing(
        self, hand_edited
    ):
        formset = formset_factory(make_form(show_hidden_initial=True), extra=1)(
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-0-when_year": "1990",
                "initial-form-0-when": hand_edited,
            }
        )

        assert formset.is_valid()
        assert formset.forms[0].cleaned_data["when"] == PartialDate(1990)
