import datetime

import pytest
from django.apps import apps
from django.core.management import call_command
from django.template import engines
from django.test import modify_settings, override_settings
from django.utils import translation
from django.utils.formats import reset_format_cache

from partial_dates import PartialDate
from partial_dates.templatetags.partial_dates import partial_date


def render(source, **context):
    return engines["django"].from_string(source).render(context)


class TestPartialDateFilter:
    @pytest.mark.parametrize(
        ("language", "value", "expected"),
        [
            ("en", PartialDate(1990), "1990"),
            ("en", PartialDate(1990, 6), "June 1990"),
            ("en", PartialDate(1990, 6, 14), "June 14, 1990"),
            ("de", PartialDate(1990, 6, 14), "14. Juni 1990"),
            ("ja", PartialDate(1990, 6), "1990年6月"),
        ],
    )
    def test_a_value_renders_its_display_form_for_the_active_language(
        self, language, value, expected
    ):
        with translation.override(language):
            text = render(
                "{% load partial_dates %}{{ value|partial_date }}", value=value
            )

        assert text == expected

    def test_none_renders_empty_text_and_default_supplies_the_fallback(self):
        template = "{% load partial_dates %}[{{ value|partial_date }}]"
        fallback = "{% load partial_dates %}{{ value|partial_date|default:'none' }}"

        assert render(template, value=None) == "[]"
        assert render(fallback, value=None) == "none"

    @pytest.mark.parametrize(
        "value",
        ["1990-06", 1990, 1990.5, datetime.date(1990, 6, 14), object(), [], {}],
    )
    def test_anything_that_is_not_a_partial_date_renders_empty_text(self, value):
        assert (
            render("{% load partial_dates %}{{ value|partial_date }}", value=value)
            == ""
        )

    def test_a_name_missing_from_the_context_renders_empty_text(self):
        assert render("{% load partial_dates %}{{ missing|partial_date }}") == ""

    def test_the_output_is_not_marked_safe(self):
        with translation.override("en"):
            result = partial_date(PartialDate(1990, 6, 14))

        assert not hasattr(result, "__html__")

    @pytest.fixture
    def project_formats(self):
        reset_format_cache()
        with override_settings(FORMAT_MODULE_PATH=["tests.formats"]):
            yield
        reset_format_cache()

    def test_a_format_that_emits_markup_is_escaped_with_autoescape_on(
        self, project_formats
    ):
        value = PartialDate(1990, 6, 14)
        with translation.override("en"):
            text = render(
                "{% load partial_dates %}{{ value|partial_date }}", value=value
            )

        assert text == "&lt;14&gt;/06/1990"


class TestAppEntry:
    def test_the_app_adds_no_model(self):
        assert list(apps.get_app_config("partial_dates").get_models()) == []

    def test_makemigrations_finds_nothing_to_make(self, db):
        call_command("makemigrations", check=True, dry_run=True)

    @modify_settings(INSTALLED_APPS={"remove": "partial_dates"})
    def test_the_python_route_works_without_the_entry(self):
        with translation.override("de"):
            assert PartialDate(1990, 6, 14).display_form() == "14. Juni 1990"
