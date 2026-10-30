from datetime import datetime

import pytest
from django.db import connection, models

from partial_dates.conversion import OldPartialDateField

OLD_TYPES = {"postgresql": "timestamp with time zone", "sqlite": "datetime"}


@pytest.mark.django_db(transaction=True)
class TestOldPartialDateField:
    def test_column_is_the_old_type(self, build_state, create_tables, describe_column):
        create_tables(build_state("oldcol", {"seen": OldPartialDateField(null=True)}))

        column = describe_column("oldcol", "seen")

        assert column["type"] == OLD_TYPES[connection.vendor]

    def test_row_written_by_raw_sql_reads_back_and_saves_unchanged(
        self, build_state, create_tables, insert_rows, read_column
    ):
        state = build_state("oldcol", {"seen": OldPartialDateField(null=True)})
        create_tables(state)
        insert_rows("oldcol", "seen", ["1990-06-01 00:00:01", None])
        before = read_column("oldcol", "seen")
        thing = state.apps.get_model("conv", "Thing")

        row = thing.objects.get(pk=before[0][0])
        row.save()

        assert row.seen.replace(tzinfo=None) == datetime(1990, 6, 1, 0, 0, 1)
        assert read_column("oldcol", "seen") == before

    def test_every_field_option_passes_through_deconstruct(self):
        field = OldPartialDateField(
            null=True,
            blank=True,
            db_index=True,
            db_column="when_seen",
            help_text="When it was seen.",
            verbose_name="seen",
            default=None,
        )

        _, path, args, kwargs = field.deconstruct()

        assert path == "partial_dates.conversion.OldPartialDateField"
        assert args == []
        assert kwargs == {
            "null": True,
            "blank": True,
            "db_index": True,
            "db_column": "when_seen",
            "help_text": "When it was seen.",
            "verbose_name": "seen",
            "default": None,
        }
        assert isinstance(field, models.Field)
