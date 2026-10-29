import pytest
from django.core.management import call_command
from django.db import DataError, IntegrityError, connection, transaction
from django.db.migrations.writer import MigrationWriter

from partial_dates import PartialDate, PartialDateField
from tests.models import Record


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
