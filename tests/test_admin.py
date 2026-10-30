import html
import json
import re
import sys
import types

import pytest
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.templatetags.admin_list import result_headers
from django.contrib.auth.models import Permission, User
from django.urls import path, reverse
from django.utils.html import strip_tags

from partial_dates import PartialDate
from partial_dates.admin import PartialDateDisplayMixin
from partial_dates.forms import PartialDateField
from tests.factories import EventFactory, NoteFactory, RecordFactory
from tests.models import Note, Record


def part(name, year="", month="", day=""):
    return {f"{name}_year": year, f"{name}_month": month, f"{name}_day": day}


def record_post(date=None, note=None, defaulted=None):
    """The posted body of the Record form with its Note inline."""
    body = {
        **part("date", *(date or ())),
        **part("other"),
        **part("defaulted", *(defaulted or ("1990",))),
        "note_set-TOTAL_FORMS": "1",
        "note_set-INITIAL_FORMS": "0",
        "note_set-MIN_NUM_FORMS": "0",
        "note_set-MAX_NUM_FORMS": "1000",
        "note_set-0-id": "",
        "note_set-0-record": "",
        **part("note_set-0-drafted", "1990", "6"),
        **part("note_set-0-reviewed", "2000", "3"),
        "initial-note_set-0-reviewed": "2000-03",
    }
    if note:
        body.update(
            part("note_set-0-drafted", *note[0]),
            **part("note_set-0-reviewed", *note[1]),
        )
    return body


@pytest.fixture
def staff(db):
    user = User.objects.create_user("staff.user", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="tests",
            content_type__model__in=["record", "note", "event"],
        )
    )
    return user


@pytest.fixture
def admin_site(client, staff):
    client.force_login(staff)
    return client


@pytest.fixture
def serve(settings, monkeypatch):
    """Serve the given models on a fresh admin site, each with its own admin class."""

    def serve(*registrations):
        site = AdminSite(name="shown")
        for model, admin_class in registrations:
            site.register(model, admin_class)
        urls = types.ModuleType("shown_urls")
        urls.urlpatterns = [path("admin/", site.urls)]
        monkeypatch.setitem(sys.modules, urls.__name__, urls)
        settings.ROOT_URLCONF = urls.__name__
        return site

    return serve


def cells(response, name):
    """The text of every cell in the column of a field on a change list."""
    found = re.findall(
        rf'class="field-{name}[^"]*"[^>]*>(.*?)</t[dh]>',
        response.content.decode(),
        re.DOTALL,
    )
    return [html.unescape(strip_tags(cell)).strip() for cell in found]


@pytest.mark.django_db
class TestAddingInTheAdmin:
    @pytest.mark.parametrize(
        ("entered", "expected"),
        [
            (("1990",), PartialDate(1990)),
            (("1990", "6"), PartialDate(1990, 6)),
            (("1990", "6", "14"), PartialDate(1990, 6, 14)),
        ],
    )
    def test_a_staff_user_adds_a_record_at_each_precision(
        self, admin_site, entered, expected
    ):
        response = admin_site.post(
            reverse("admin:tests_record_add"), record_post(date=entered)
        )

        assert response.status_code == 302
        assert Record.objects.get().date == expected

    def test_the_add_form_offers_the_three_selects_with_no_override(self, admin_site):
        response = admin_site.get(reverse("admin:tests_record_add"))

        form = response.context["adminform"].form
        assert isinstance(form.fields["date"], PartialDateField)
        for name in ("date_year", "date_month", "date_day"):
            assert f'name="{name}"' in response.content.decode()

    def test_a_note_in_the_inline_holds_the_values_entered(self, admin_site):
        body = record_post(date=("1990",), note=(("1991", "2"), ("2001", "", "")))

        response = admin_site.post(reverse("admin:tests_record_add"), body)

        assert response.status_code == 302
        note = Note.objects.get()
        assert note.drafted == PartialDate(1991, 2)
        assert note.reviewed == PartialDate(2001)

    def test_an_inline_left_as_it_opened_adds_no_note(self, admin_site):
        response = admin_site.post(
            reverse("admin:tests_record_add"), record_post(date=("1990",))
        )

        assert response.status_code == 302
        assert not Note.objects.exists()

    def test_a_staff_user_adds_an_event_with_a_required_unique_date(self, admin_site):
        EventFactory(occurred="1990-06")

        response = admin_site.post(
            reverse("admin:tests_event_add"), part("occurred", "1990", "6")
        )

        assert response.status_code == 200
        assert response.context["adminform"].form.has_error("occurred", code="unique")


@pytest.mark.django_db
class TestChangingInTheAdmin:
    def change_body(self, record, saved, **fields):
        return {
            **record_post(**fields),
            "note_set-INITIAL_FORMS": "1",
            "note_set-0-id": str(saved.pk),
            "note_set-0-record": str(record.pk),
        }

    @pytest.mark.parametrize(
        ("stored", "entered", "expected"),
        [
            ("1990", ("1990", "6"), PartialDate(1990, 6)),
            ("1990-06-14", ("1990",), PartialDate(1990)),
        ],
    )
    def test_a_staff_user_changes_the_precision_of_a_record(
        self, admin_site, stored, entered, expected
    ):
        record = RecordFactory(date=stored)
        saved = NoteFactory(record=record)

        response = admin_site.post(
            reverse("admin:tests_record_change", args=[record.pk]),
            self.change_body(
                record,
                saved,
                date=entered,
                note=(("1990", "6"), ("2000", "3")),
            ),
        )

        assert response.status_code == 302
        record.refresh_from_db()
        assert record.date == expected

    def test_an_unchanged_save_records_that_nothing_changed(self, admin_site):
        record = RecordFactory(date="1990-06-14")
        saved = NoteFactory(record=record)

        response = admin_site.post(
            reverse("admin:tests_record_change", args=[record.pk]),
            self.change_body(
                record,
                saved,
                date=("1990", "6", "14"),
                note=(("1990", "6"), ("2000", "3")),
            ),
        )

        assert response.status_code == 302
        assert json.loads(LogEntry.objects.get().change_message) == []
        record.refresh_from_db()
        assert record.date == PartialDate(1990, 6, 14)

    def test_the_change_form_opens_on_the_stored_parts(self, admin_site):
        record = RecordFactory(date="1990-06")

        response = admin_site.get(
            reverse("admin:tests_record_change", args=[record.pk])
        )

        form = response.context["adminform"].form
        assert form["date"].value() == PartialDate(1990, 6)


@pytest.mark.django_db
class TestRefusalsInTheAdmin:
    def test_a_day_with_no_month_comes_back_with_the_error_on_the_field(
        self, admin_site
    ):
        response = admin_site.post(
            reverse("admin:tests_record_add"), record_post(date=("1990", "", "14"))
        )

        assert response.status_code == 200
        form = response.context["adminform"].form
        assert form.has_error("date", code="incomplete")
        assert not Record.objects.exists()

    def test_text_in_a_part_returns_the_change_form_with_the_invalid_error(
        self, admin_site
    ):
        record = RecordFactory(date="1990")

        response = admin_site.post(
            reverse("admin:tests_record_change", args=[record.pk]),
            {
                **record_post(date=("1990", "x")),
                "note_set-0-record": str(record.pk),
            },
        )

        assert response.status_code == 200
        form = response.context["adminform"].form
        assert form.has_error("date", code="invalid")
        record.refresh_from_db()
        assert record.date == PartialDate(1990)


class ListedRecordAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
    list_display = ["date", "other"]


@pytest.mark.django_db
class TestAdminList:
    @pytest.mark.parametrize(
        "stored", [PartialDate(1990), PartialDate(1990, 6), PartialDate(1990, 6, 14)]
    )
    def test_the_column_shows_the_display_form(self, admin_site, serve, stored):
        serve((Record, ListedRecordAdmin))
        record = RecordFactory(date=stored)

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        assert cells(response, "date") == [record.date.display_form()]

    @pytest.mark.parametrize("stored", [PartialDate(1990, 6), PartialDate(1990, 6, 14)])
    def test_the_iso_form_is_gone_from_the_page(self, admin_site, serve, stored):
        serve((Record, ListedRecordAdmin))
        RecordFactory(date=stored)

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        assert stored.isoformat() not in response.content.decode()

    def test_the_column_keeps_the_heading_of_the_model_field(self, admin_site, serve):
        serve((Record, ListedRecordAdmin))

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        heading = str(Record._meta.get_field("date").verbose_name)
        headers = result_headers(response.context["cl"])
        assert heading in [header["text"] for header in headers]

    @pytest.mark.parametrize(("order", "reverse_order"), [("1", False), ("-1", True)])
    def test_the_column_sorts_by_the_stored_order(
        self, admin_site, serve, order, reverse_order
    ):
        serve((Record, ListedRecordAdmin))
        for stored in [
            PartialDate(1991),
            PartialDate(1990, 6),
            PartialDate(1990),
            PartialDate(1990, 6, 14),
        ]:
            RecordFactory(date=stored)

        response = admin_site.get(
            reverse("admin:tests_record_changelist"), {"o": order}
        )

        shown = [record.date for record in response.context["cl"].result_list]
        assert shown == sorted(shown, reverse=reverse_order)
        heading = str(Record._meta.get_field("date").verbose_name)
        headers = {h["text"]: h for h in result_headers(response.context["cl"])}
        assert headers[heading]["sortable"]

    def test_the_declared_ordering_is_the_stored_order(self, admin_site, serve):
        class OrderedRecordAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
            list_display = ["date"]
            ordering = ["date"]

        serve((Record, OrderedRecordAdmin))
        for stored in [PartialDate(1991), PartialDate(1990, 6), PartialDate(1990)]:
            RecordFactory(date=stored)

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        shown = [record.date for record in response.context["cl"].result_list]
        assert shown == sorted(shown)

    def test_the_first_column_links_to_the_row_by_default(self, admin_site, serve):
        serve((Record, ListedRecordAdmin))
        record = RecordFactory(date=PartialDate(1990, 6))

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        url = reverse("admin:tests_record_change", args=[record.pk])
        assert re.search(
            rf'<a href="{url}[^"]*">{record.date.display_form()}</a>',
            response.content.decode(),
        )

    def test_a_column_named_in_the_links_links_to_the_row(self, admin_site, serve):
        class LinkedRecordAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
            list_display = ["other", "date"]
            list_display_links = ["date"]

        serve((Record, LinkedRecordAdmin))
        record = RecordFactory(date=PartialDate(1990, 6), other=PartialDate(1991))

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        url = reverse("admin:tests_record_change", args=[record.pk])
        page = response.content.decode()
        assert re.search(
            rf'<a href="{url}[^"]*">{record.date.display_form()}</a>', page
        )
        assert not re.search(
            rf'<a href="{url}[^"]*">{record.other.display_form()}</a>', page
        )

    def test_a_field_in_list_editable_keeps_its_selects_and_saves(
        self, admin_site, serve
    ):
        class EditableRecordAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
            list_display = ["date", "defaulted"]
            list_editable = ["defaulted"]

        serve((Record, EditableRecordAdmin))
        record = RecordFactory(date=PartialDate(1990, 6))
        url = reverse("admin:tests_record_changelist")

        page = admin_site.get(url).content.decode()
        response = admin_site.post(
            url,
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": str(record.pk),
                **part("form-0-defaulted", "2001"),
                "_save": "Save",
            },
        )

        assert 'name="form-0-defaulted_year"' in page
        assert response.status_code == 302
        record.refresh_from_db()
        assert record.defaulted == PartialDate(2001)
        assert record.date == PartialDate(1990, 6)

    def test_an_empty_value_shows_the_empty_display_of_the_admin(
        self, admin_site, serve
    ):
        site = serve((Record, ListedRecordAdmin))
        RecordFactory(date=None)

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        empty = site.get_model_admin(Record).get_empty_value_display()
        assert cells(response, "date") == [empty]

    def test_an_empty_value_shows_a_custom_empty_display(self, admin_site, serve):
        class BlankRecordAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
            list_display = ["date"]
            empty_value_display = "no date known"

        serve((Record, BlankRecordAdmin))
        RecordFactory(date=None)

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        assert cells(response, "date") == ["no date known"]

    def test_a_method_and_a_path_through_a_relation_are_left_alone(
        self, admin_site, serve
    ):
        class WorkedRecordAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
            list_display = ["when"]

            def when(self, obj):
                return f"on {obj.date}"

        class WorkedNoteAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
            list_display = ["drafted", "record__date"]

        serve((Record, WorkedRecordAdmin), (Note, WorkedNoteAdmin))
        record = RecordFactory(date=PartialDate(1990, 6))
        note = NoteFactory(record=record, drafted=PartialDate(1992, 3))

        records = admin_site.get(reverse("admin:tests_record_changelist"))
        notes = admin_site.get(reverse("admin:tests_note_changelist"))

        assert cells(records, "when") == ["on 1990-06"]
        assert cells(notes, "drafted") == [note.drafted.display_form()]
        assert cells(notes, "record__date") == ["1990-06"]

    def test_an_admin_with_no_mixin_shows_the_iso_form(self, admin_site, serve):
        class PlainRecordAdmin(admin.ModelAdmin):
            list_display = ["date"]

        serve((Record, PlainRecordAdmin))
        RecordFactory(date=PartialDate(1990, 6))

        response = admin_site.get(reverse("admin:tests_record_changelist"))

        assert cells(response, "date") == ["1990-06"]
