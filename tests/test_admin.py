import json

import pytest
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission, User
from django.urls import reverse

from partial_dates import PartialDate
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
