import pytest
from django.core.management import call_command
from django.db import connection
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
