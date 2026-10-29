import datetime
import io
import json
from pathlib import Path

import pytest
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.serializers.base import DeserializationError
from django.db import DataError, IntegrityError, connection, transaction
from django.db.migrations.writer import MigrationWriter

from partial_dates import PartialDate, PartialDateField
from tests.factories import RecordFactory
from tests.models import Event, Record


@pytest.mark.django_db
class TestColumn:
    @pytest.fixture
    def description(self):
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(
                cursor, Record._meta.db_table
            )
        return {column.name: column for column in columns}

    @pytest.mark.parametrize("name", ["date", "other", "defaulted"])
    def test_the_column_is_ten_characters_of_text(self, description, name):
        column = description[name]

        assert (column.internal_size or column.display_size) == 10
        assert (
            connection.introspection.get_field_type(column.type_code, column)
            == "CharField"
        )

    def test_the_column_is_byte_order_collated_on_postgresql(self, description):
        if connection.vendor != "postgresql":
            assert description["date"].collation is None
        else:
            assert description["date"].collation == "C"

    def test_deconstruct_carries_no_max_length(self):
        _, _, _, kwargs = PartialDateField().deconstruct()

        assert "max_length" not in kwargs

    def test_a_partial_date_default_deconstructs_to_its_iso_form(self):
        field = PartialDateField(default=PartialDate(1990))

        _, _, _, kwargs = field.deconstruct()

        assert kwargs["default"] == "1990"

    def test_a_partial_date_default_serialises_in_a_migration(self):
        field = PartialDateField(default=PartialDate(1990, 6))

        serialised, _ = MigrationWriter.serialize(field)

        assert "'1990-06'" in serialised

    def test_a_string_default_is_left_alone(self):
        _, _, _, kwargs = PartialDateField(default="1990").deconstruct()

        assert kwargs["default"] == "1990"

    def test_a_callable_default_is_left_alone(self):
        _, _, _, kwargs = PartialDateField(default=dict).deconstruct()

        assert kwargs["default"] is dict

    def test_max_length_is_refused(self):
        with pytest.raises(TypeError):
            PartialDateField(max_length=5)

    def test_the_package_exports_the_field(self):
        import partial_dates

        assert "PartialDateField" in partial_dates.__all__

    def test_the_test_app_needs_no_migration(self):
        call_command("makemigrations", "tests", check=True, dry_run=True)


REFUSED = [
    pytest.param(text, (IntegrityError,), id=repr(text))
    for text in [
        "1990-6",
        "990",
        "19900614",
        "1990?",
        "1990~",
        " 1990",
        "1990 ",
        "",
        "0000",
        "0000-01",
        "1990-00",
        "1990-13",
        "1990-02-30",
        "1900-02-29",
        "1990-04-31",
        "1990-06-00",
        "1990-06-32",
        "1991-02-29",
        "2100-02-29",
        "1990-06-31",
        "1990-09-31",
        "1990-11-31",
        "199a",
        "1990/06",
        "١٩٩٠",
    ]
] + [
    pytest.param("1990-06-14T00:00", (IntegrityError, DataError), id="overlong"),
    pytest.param("1990-06-14-00", (IntegrityError, DataError), id="eleven-characters"),
    pytest.param(
        "1990\x00junk", (IntegrityError, DataError, ValueError), id="embedded-nul"
    ),
]

ACCEPTED = [
    ("1990", PartialDate(1990)),
    ("1990-06", PartialDate(1990, 6)),
    ("1990-06-14", PartialDate(1990, 6, 14)),
    ("0001", PartialDate(1)),
    ("9999-12-31", PartialDate(9999, 12, 31)),
    ("2000-02-29", PartialDate(2000, 2, 29)),
    ("1996-02-29", PartialDate(1996, 2, 29)),
    ("0990", PartialDate(990)),
    ("0004-02-29", PartialDate(4, 2, 29)),
    ("2400-02-29", PartialDate(2400, 2, 29)),
    ("1990-06-30", PartialDate(1990, 6, 30)),
    ("1990-12-31", PartialDate(1990, 12, 31)),
]


@pytest.mark.django_db
class TestDatabaseCheck:
    table = connection.ops.quote_name(Record._meta.db_table)

    def insert(self, column, text):
        sql = (
            f"INSERT INTO {self.table} ({connection.ops.quote_name(column)}, "
            f"{connection.ops.quote_name('defaulted')}) VALUES (%s, %s)"
        )
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql, [text, "1990"])

    def update(self, column, text, pk):
        sql = (
            f"UPDATE {self.table} SET {connection.ops.quote_name(column)} = %s "
            f"WHERE {connection.ops.quote_name('id')} = %s"
        )
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql, [text, pk])

    @pytest.mark.parametrize(("text", "errors"), REFUSED)
    def test_malformed_text_is_refused_on_insert(self, text, errors):
        with pytest.raises(errors):
            self.insert("date", text)

        assert not Record.objects.exists()

    @pytest.mark.parametrize(("text", "errors"), REFUSED)
    def test_malformed_text_is_refused_on_update(self, record, text, errors):
        with pytest.raises(errors):
            self.update("date", text, record.pk)

        assert Record.objects.get(pk=record.pk).date is None

    @pytest.mark.parametrize(("text", "expected"), ACCEPTED)
    def test_well_formed_text_is_accepted_and_read_back_as_a_partial_date(
        self, text, expected
    ):
        self.insert("date", text)

        assert Record.objects.get().date == expected

    def test_null_is_accepted(self):
        self.insert("date", None)

        assert Record.objects.get().date is None

    @pytest.mark.parametrize("column", ["date", "other"])
    def test_each_field_of_a_model_is_checked_on_its_own(self, column):
        with pytest.raises(IntegrityError):
            self.insert(column, "1990-6")


@pytest.mark.django_db
class TestSavingAndReading:
    def stored(self, pk, column="date"):
        sql = (
            f"SELECT {connection.ops.quote_name(column)} "
            f"FROM {connection.ops.quote_name(Record._meta.db_table)} "
            f"WHERE {connection.ops.quote_name('id')} = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            return cursor.fetchone()[0]

    @pytest.mark.parametrize(
        ("value", "text"),
        [
            (PartialDate(1990), "1990"),
            (PartialDate(1990, 6), "1990-06"),
            (PartialDate(1990, 6, 14), "1990-06-14"),
            (PartialDate(1), "0001"),
            (PartialDate(990), "0990"),
            (PartialDate(9999, 12, 31), "9999-12-31"),
        ],
    )
    def test_a_partial_date_is_stored_as_its_iso_form_and_read_back_equal(
        self, value, text
    ):
        record = Record.objects.create(date=value)

        record.refresh_from_db()

        assert record.date == value
        assert self.stored(record.pk) == text

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1990", PartialDate(1990)),
            ("1990-06", PartialDate(1990, 6)),
            ("1990-06-14", PartialDate(1990, 6, 14)),
        ],
    )
    def test_iso_text_is_saved_and_read_back_as_the_value(self, text, expected):
        record = Record.objects.create(date=text)

        record.refresh_from_db()

        assert record.date == expected
        assert self.stored(record.pk) == text

    @pytest.mark.parametrize("empty", [None, ""])
    def test_an_empty_value_is_stored_as_null(self, empty):
        record = Record.objects.create(date=empty)

        record.refresh_from_db()

        assert record.date is None
        assert self.stored(record.pk) is None

    def test_a_required_field_left_empty_is_refused_by_the_database(self):
        with pytest.raises(IntegrityError):
            Event.objects.create()

    def test_a_default_given_as_text_is_stored(self):
        record = Record.objects.create()

        record.refresh_from_db()

        assert record.defaulted == PartialDate(1990)

    def test_a_default_given_as_a_partial_date_is_prepared_as_its_iso_form(self):
        field = PartialDateField(default=PartialDate(1990))
        field.set_attributes_from_name("when")

        assert field.get_default() == PartialDate(1990)
        assert field.get_prep_value(field.get_default()) == "1990"


@pytest.mark.django_db
class TestRefusedWrites:
    @pytest.fixture
    def rows(self):
        return [RecordFactory(date=PartialDate(1990, n)) for n in (1, 2)]

    def values(self):
        return list(Record.objects.order_by("pk").values_list("date", flat=True))

    @pytest.fixture(
        params=["1990-6", "990", datetime.date(1990, 6, 14), 1990],
        ids=["short-month", "short-year", "date", "int"],
    )
    def bad(self, request):
        return request.param

    def test_save_refuses_the_value(self, rows, bad):
        record = Record(date=bad)

        with pytest.raises(ValueError), transaction.atomic():
            record.save()

        assert self.values() == [PartialDate(1990, 1), PartialDate(1990, 2)]

    def test_create_refuses_the_value(self, rows, bad):
        with pytest.raises(ValueError), transaction.atomic():
            Record.objects.create(date=bad)

        assert self.values() == [PartialDate(1990, 1), PartialDate(1990, 2)]

    def test_update_refuses_the_value(self, rows, bad):
        with pytest.raises(ValueError), transaction.atomic():
            Record.objects.update(date=bad)

        assert self.values() == [PartialDate(1990, 1), PartialDate(1990, 2)]

    def test_bulk_create_refuses_the_value(self, rows, bad):
        with pytest.raises(ValueError), transaction.atomic():
            Record.objects.bulk_create([Record(date=bad)])

        assert self.values() == [PartialDate(1990, 1), PartialDate(1990, 2)]

    def test_bulk_update_refuses_the_value(self, rows, bad):
        rows[0].date = bad

        with pytest.raises(ValueError), transaction.atomic():
            Record.objects.bulk_update(rows, ["date"])

        assert self.values() == [PartialDate(1990, 1), PartialDate(1990, 2)]


@pytest.mark.django_db
class TestValidation:
    def test_full_clean_reports_text_that_is_not_a_partial_date(self):
        record = Record(date="1990-6")

        with pytest.raises(ValidationError) as raised:
            record.full_clean()

        assert raised.value.error_dict["date"][0].code == "invalid"

    def test_full_clean_leaves_a_partial_date_on_the_attribute(self):
        record = Record(date="1990-06")

        record.full_clean()

        assert record.date == PartialDate(1990, 6)


@pytest.mark.django_db
class TestFiltering:
    @pytest.fixture
    def rows(self):
        return {
            text: RecordFactory(date=text)
            for text in ["1990", "1990-01", "1990-01-01", None]
        }

    def test_filtering_by_a_partial_date_finds_only_that_value(self, rows):
        found = Record.objects.filter(date=PartialDate(1990))

        assert list(found) == [rows["1990"]]

    def test_filtering_by_iso_text_finds_only_that_value(self, rows):
        found = Record.objects.filter(date="1990")

        assert list(found) == [rows["1990"]]

    def test_get_finds_an_event_by_a_partial_date(self, event):
        found = Event.objects.get(occurred=PartialDate.fromisoformat(event.occurred))

        assert found == event

    def test_get_finds_an_event_by_iso_text(self, event):
        assert Event.objects.get(occurred=event.occurred) == event

    def test_a_unique_field_refuses_a_second_row_with_the_same_value(self):
        Event.objects.create(occurred=PartialDate(1990))

        with pytest.raises(IntegrityError), transaction.atomic():
            Event.objects.create(occurred="1990")

    def test_a_db_index_field_has_an_index(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, Event._meta.db_table
            )

        indexed = [
            name
            for name, constraint in constraints.items()
            if constraint["index"] and constraint["columns"] == ["indexed"]
        ]
        assert indexed


@pytest.mark.django_db
class TestFixtures:
    fixtures_dir = Path(__file__).parent / "fixtures"
    texts = {1: "1990", 2: "1990-06", 3: "1990-06-14", 4: None}
    handwritten = {
        "json": json.dumps(
            [
                {"model": "tests.record", "pk": pk, "fields": {"date": text}}
                for pk, text in {1: "1990", 2: "1990-06", 3: "1990-06-14"}.items()
            ]
        ),
        "jsonl": "\n".join(
            json.dumps({"model": "tests.record", "pk": pk, "fields": {"date": text}})
            for pk, text in {1: "1990", 2: "1990-06", 3: "1990-06-14"}.items()
        ),
        "xml": (
            '<?xml version="1.0" encoding="utf-8"?><django-objects version="1.0">'
            + "".join(
                f'<object model="tests.record" pk="{pk}">'
                f'<field name="date" type="CharField">{text}</field></object>'
                for pk, text in {1: "1990", 2: "1990-06", 3: "1990-06-14"}.items()
            )
            + "</django-objects>"
        ),
    }
    invalid = {
        "json": '[{"model": "tests.record", "pk": 1, "fields": {"date": "1990-6"}}]',
        "jsonl": '{"model": "tests.record", "pk": 1, "fields": {"date": "1990-6"}}',
        "xml": (
            '<?xml version="1.0" encoding="utf-8"?><django-objects version="1.0">'
            '<object model="tests.record" pk="1">'
            '<field name="date" type="CharField">1990-6</field></object>'
            "</django-objects>"
        ),
    }

    @pytest.fixture
    def rows(self):
        return [RecordFactory(pk=pk, date=text) for pk, text in self.texts.items()]

    def dump(self, fmt):
        out = io.StringIO()
        call_command(
            "dumpdata",
            "tests.Record",
            format=fmt,
            indent=2 if fmt != "jsonl" else None,
            stdout=out,
        )
        return out.getvalue()

    def test_serialising_an_instance_holding_empty_text_writes_null(self):
        record = Record(pk=1, date="")

        text = serializers.serialize("json", [record])

        assert json.loads(text)[0]["fields"]["date"] is None

    @pytest.mark.parametrize("fmt", ["json", "jsonl", "xml"])
    def test_dumpdata_equals_the_committed_fixture(self, rows, fmt):
        committed = (self.fixtures_dir / f"records.{fmt}").read_text()

        assert self.dump(fmt) == committed

    @pytest.mark.parametrize("fmt", ["json", "jsonl", "xml"])
    def test_loaddata_of_the_committed_fixture_gives_the_values(self, fmt):
        call_command("loaddata", f"records.{fmt}", verbosity=0)

        loaded = {record.pk: record.date for record in Record.objects.all()}
        assert loaded == {
            1: PartialDate(1990),
            2: PartialDate(1990, 6),
            3: PartialDate(1990, 6, 14),
            4: None,
        }

    @pytest.mark.parametrize("fmt", ["json", "jsonl", "xml"])
    def test_loaddata_reads_a_hand_written_fixture_of_iso_texts(self, tmp_path, fmt):
        path = tmp_path / f"hand.{fmt}"
        path.write_text(self.handwritten[fmt])

        call_command("loaddata", str(path), verbosity=0)

        loaded = {record.pk: record.date for record in Record.objects.all()}
        assert loaded == {
            1: PartialDate(1990),
            2: PartialDate(1990, 6),
            3: PartialDate(1990, 6, 14),
        }

    @pytest.mark.parametrize("fmt", ["json", "jsonl", "xml"])
    def test_loaddata_refuses_text_that_is_not_a_partial_date(self, tmp_path, fmt):
        path = tmp_path / f"bad.{fmt}"
        path.write_text(self.invalid[fmt])

        with pytest.raises((DeserializationError, ValidationError)):
            call_command("loaddata", str(path), verbosity=0)

        assert not Record.objects.exists()
