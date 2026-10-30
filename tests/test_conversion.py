from datetime import datetime

import pytest
from django.db import DatabaseError, IntegrityError, connection, models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.graph import MigrationGraph

from partial_dates import PartialDate, PartialDateField
from partial_dates.conversion import ConvertPartialDateField, OldPartialDateField

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


CONVERSIONS = [
    ("1990-01-01 00:00:00", "1990"),
    ("1990-06-01 00:00:01", "1990-06"),
    ("1990-06-14 00:00:02", "1990-06-14"),
    ("0990-03-01 00:00:01", "0990-03"),
    ("0001-01-01 00:00:00", "0001"),
    ("0001-01-01 00:00:01", "0001-01"),
    ("0001-01-01 00:00:02", "0001-01-01"),
    ("9999-01-01 00:00:00", "9999"),
    ("9999-12-01 00:00:01", "9999-12"),
    ("9999-12-31 00:00:02", "9999-12-31"),
]


def indexed(table):
    return {"indexes": [models.Index(fields=["seen"], name=f"{table}_seen_idx")]}


def constrained(table):
    return {
        "constraints": [
            models.UniqueConstraint(fields=["seen"], name=f"{table}_seen_uniq")
        ]
    }


SHAPES = {
    "required": ({}, None),
    "nullable": ({"null": True}, None),
    "db_index": ({"null": True, "db_index": True}, None),
    "unique": ({"unique": True}, None),
    "nullable_unique": ({"null": True, "unique": True}, None),
    "meta_indexes": ({"null": True}, indexed),
    "unique_constraint": ({"null": True}, constrained),
}


@pytest.mark.django_db(transaction=True)
class TestConversion:
    @pytest.mark.parametrize(("stored", "expected"), CONVERSIONS)
    def test_value_converts_to_its_iso_form(
        self, convert, read_column, stored, expected
    ):
        convert("conv_values", [stored], null=True)

        assert read_column("conv_values", "seen") == [(1, expected)]

    def test_field_reads_back_the_partial_dates(self, convert):
        after = convert(
            "conv_reads",
            ["1990-01-01 00:00:00", "1990-06-01 00:00:01", "1990-06-14 00:00:02"],
        )

        thing = after.apps.get_model("conv", "Thing")
        assert [row.seen for row in thing.objects.order_by("pk")] == [
            PartialDate.fromisoformat(text)
            for text in ("1990", "1990-06", "1990-06-14")
        ]

    def test_empty_values_stay_empty(self, convert, read_column):
        convert("conv_empty", [None, "1990-01-01 00:00:00", None], null=True)

        assert read_column("conv_empty", "seen") == [(1, None), (2, "1990"), (3, None)]

    def test_required_field_stays_required(self, convert, insert_rows):
        convert("conv_required", ["1990-01-01 00:00:00"])

        with pytest.raises(IntegrityError):
            insert_rows("conv_required", "seen", [None])

    @pytest.mark.parametrize("shape", SHAPES)
    def test_converted_column_equals_a_new_one(
        self, shape, convert, build_state, create_tables, describe_column
    ):
        options, meta = SHAPES[shape]
        old, new = f"conv_{shape}_old", f"conv_{shape}_new"
        convert(old, ["1990-01-01 00:00:00"], meta(old) if meta else None, **options)
        create_tables(
            build_state(
                new,
                {"seen": PartialDateField(**options)},
                **(meta(new) if meta else {}),
            )
        )

        assert describe_column(old, "seen") == describe_column(new, "seen")

    @pytest.mark.parametrize("shape", ["unique", "unique_constraint"])
    def test_uniqueness_is_enforced(self, shape, convert, insert_rows):
        options, meta = SHAPES[shape]
        table = f"conv_{shape}"
        convert(
            table, ["1990-01-01 00:00:00"], meta(table) if meta else None, **options
        )

        with pytest.raises(IntegrityError):
            insert_rows(table, "seen", ["1990"])

    def test_check_refuses_malformed_text(self, convert, insert_rows):
        convert("conv_check", ["1990-01-01 00:00:00"], null=True)

        with pytest.raises(DatabaseError):
            insert_rows("conv_check", "seen", ["1990-13"])

    def test_state_matches_the_target_field(self, build_state):
        before = build_state("conv_state", {"seen": OldPartialDateField(null=True)})
        operation = ConvertPartialDateField(
            "thing", "seen", PartialDateField(null=True)
        )
        after = before.clone()
        operation.state_forwards("conv", after)
        target = build_state("conv_state", {"seen": PartialDateField(null=True)})

        changes = MigrationAutodetector(after, target).changes(graph=MigrationGraph())

        assert changes == {}


ZONES = [
    pytest.param(True, "America/New_York", id="use_tz-west"),
    pytest.param(True, "Asia/Tokyo", id="use_tz-east"),
    pytest.param(False, "Europe/Berlin", id="no_tz-east"),
    pytest.param(False, "America/New_York", id="no_tz-west"),
]


@pytest.mark.django_db(transaction=True)
class TestTimeZones:
    @pytest.mark.parametrize(("use_tz", "zone"), ZONES)
    def test_values_convert_to_the_date_the_old_field_read(
        self, convert, read_column, settings, use_tz, zone
    ):
        settings.USE_TZ = use_tz
        settings.TIME_ZONE = zone
        stored = {
            "1990-01-01 00:00:00": "1990",
            "1800-01-01 00:00:00": "1800",
            "1800-06-01 00:00:01": "1800-06",
            "1800-06-14 00:00:02": "1800-06-14",
            "1990-12-31 00:00:02": "1990-12-31",
        }

        convert("conv_zone", list(stored), null=True)

        assert [text for _, text in read_column("conv_zone", "seen")] == list(
            stored.values()
        )
