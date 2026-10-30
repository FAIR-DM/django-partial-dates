import os
from datetime import datetime

import pytest
from django.db import (
    DatabaseError,
    IntegrityError,
    NotSupportedError,
    connection,
    migrations,
    models,
)
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.optimizer import MigrationOptimizer
from django.db.migrations.writer import MigrationWriter

from partial_dates import PartialDate, PartialDateField
from partial_dates.conversion import (
    ConvertPartialDateField,
    OldPartialDateField,
    RefusedValuesError,
)

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


class ExcludingRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return False if model_name == "excluded" else None


@pytest.mark.django_db(transaction=True)
class TestConversionTargets:
    def test_field_with_its_own_db_column(
        self,
        build_state,
        create_tables,
        insert_rows,
        migrate,
        read_column,
        describe_column,
    ):
        options = {"null": True, "db_index": True, "db_column": "when_seen"}
        state = build_state("conv_column", {"seen": OldPartialDateField(**options)})
        create_tables(state)
        insert_rows("conv_column", "when_seen", ["1990-06-01 00:00:01"])

        migrate(
            state, ConvertPartialDateField("thing", "seen", PartialDateField(**options))
        )

        create_tables(
            build_state("conv_column_new", {"seen": PartialDateField(**options)})
        )
        assert read_column("conv_column", "when_seen") == [(1, "1990-06")]
        assert describe_column("conv_column", "when_seen") == describe_column(
            "conv_column_new", "when_seen"
        )

    def test_table_name_with_a_capital_and_a_hyphen(
        self,
        build_state,
        create_tables,
        insert_rows,
        migrate,
        read_column,
        describe_column,
    ):
        options = {"null": True, "unique": True}
        state = build_state("Field-Notes", {"seen": OldPartialDateField(**options)})
        create_tables(state)
        insert_rows("Field-Notes", "seen", ["1990-06-14 00:00:02"])

        migrate(
            state, ConvertPartialDateField("thing", "seen", PartialDateField(**options))
        )

        create_tables(
            build_state("Field-Notes-new", {"seen": PartialDateField(**options)})
        )
        assert read_column("Field-Notes", "seen") == [(1, "1990-06-14")]
        assert describe_column("Field-Notes", "seen") == describe_column(
            "Field-Notes-new", "seen"
        )

    def test_several_fields_and_models_in_one_migration(
        self, build_state, create_tables, insert_rows, migrate, read_column
    ):
        state = build_state(
            "conv_first",
            {
                "seen": OldPartialDateField(null=True),
                "heard": OldPartialDateField(null=True, db_column="when_heard"),
            },
        )
        state = build_state(
            "conv_second", {"seen": OldPartialDateField()}, name="Other", state=state
        )
        create_tables(state)
        insert_rows("conv_first", "seen", ["1990-01-01 00:00:00"])
        insert_rows("conv_first", "when_heard", ["1991-02-01 00:00:01"])
        insert_rows("conv_second", "seen", ["1992-03-04 00:00:02"])

        migrate(
            state,
            ConvertPartialDateField("thing", "seen", PartialDateField(null=True)),
            ConvertPartialDateField(
                "thing", "heard", PartialDateField(null=True, db_column="when_heard")
            ),
            ConvertPartialDateField("other", "seen", PartialDateField()),
        )

        assert read_column("conv_first", "seen") == [(1, "1990"), (2, None)]
        assert read_column("conv_first", "when_heard") == [(1, None), (2, "1991-02")]
        assert read_column("conv_second", "seen") == [(1, "1992-03-04")]

    def test_model_the_router_excludes_is_left_alone(
        self,
        settings,
        build_state,
        create_tables,
        insert_rows,
        migrate,
        read_column,
        describe_column,
    ):
        settings.DATABASE_ROUTERS = ["tests.test_conversion.ExcludingRouter"]
        state = build_state("conv_kept", {"seen": OldPartialDateField(null=True)})
        state = build_state(
            "conv_excluded",
            {"seen": OldPartialDateField(null=True)},
            name="Excluded",
            state=state,
        )
        create_tables(state)
        insert_rows("conv_kept", "seen", ["1990-01-01 00:00:00"])
        insert_rows("conv_excluded", "seen", ["1990-01-01 00:00:00"])
        before = read_column("conv_excluded", "seen")
        column = describe_column("conv_excluded", "seen")

        migrate(
            state,
            ConvertPartialDateField("thing", "seen", PartialDateField(null=True)),
            ConvertPartialDateField("excluded", "seen", PartialDateField(null=True)),
        )

        assert read_column("conv_kept", "seen") == [(1, "1990")]
        assert read_column("conv_excluded", "seen") == before
        assert describe_column("conv_excluded", "seen") == column


ON_POSTGRESQL = os.environ.get("TEST_DATABASE") == "postgresql"
REFUSED = [
    pytest.param("1990-06-14 13:45:37", "1990-06-14 13:45:37", id="time-of-day"),
    pytest.param("1990-06-14 00:00:03", "1990-06-14 00:00:03", id="seconds-3"),
    pytest.param("1990-06-14 00:00:59", "1990-06-14 00:00:59", id="seconds-59"),
    pytest.param("1990-06-14 00:00:02.5", "1990-06-14 00:00:02.5", id="fraction"),
    pytest.param("1990-06-14 00:00:00", "1990-06-14 00:00:00", id="year-off-jan-1"),
    pytest.param("1990-06-14 00:00:01", "1990-06-14 00:00:01", id="month-off-first"),
    *(
        [
            pytest.param("infinity", "infinity", id="infinity"),
            pytest.param(
                "0001-01-01 00:00:00 BC", "0001-01-01 00:00:00 BC", id="before-year-1"
            ),
            pytest.param(
                "10000-01-01 00:00:00", "10000-01-01 00:00:00", id="after-year-9999"
            ),
        ]
        if ON_POSTGRESQL
        else [
            pytest.param("1990-02-30 00:00:02", "1990-02-30 00:00:02", id="impossible"),
            pytest.param("garbage", "garbage", id="garbage"),
            pytest.param(
                "1990-06-14 00:00:02 junk", "1990-06-14 00:00:02 junk", id="trailing"
            ),
            pytest.param(19900614, "19900614", id="number"),
            pytest.param("", "", id="empty-text"),
            pytest.param(
                "1990-06-14 00:00:02+01:00",
                "1990-06-14 00:00:02+01:00",
                id="with-offset",
            ),
        ]
    ),
]


@pytest.mark.django_db(transaction=True)
class TestRefusal:
    @pytest.fixture
    def old_table(self, build_state, create_tables, insert_keyed):
        def make(table, pairs, **options):
            state = build_state(table, {"seen": OldPartialDateField(**options)})
            create_tables(state)
            insert_keyed(table, "seen", pairs)
            return state

        return make

    @pytest.mark.parametrize(("refused", "stored"), REFUSED)
    def test_refused_value_stops_the_migration_with_nothing_changed(
        self,
        old_table,
        apply_forwards,
        read_column,
        describe_column,
        refused,
        stored,
    ):
        state = old_table(
            "conv_refused",
            [
                (107, refused),
                (105, "1990-01-01 00:00:00"),
                (102, refused),
                (109, "1990-06-14 00:00:02"),
                (104, None),
            ],
            null=True,
        )
        rows, column = (
            read_column("conv_refused", "seen"),
            describe_column("conv_refused", "seen"),
        )
        operation = ConvertPartialDateField(
            "thing", "seen", PartialDateField(null=True)
        )

        with pytest.raises(RefusedValuesError) as raised:
            apply_forwards(operation, state)

        assert read_column("conv_refused", "seen") == rows
        assert describe_column("conv_refused", "seen") == column
        assert raised.value.model == "conv.Thing"
        assert raised.value.field == "seen"
        assert raised.value.count == 2
        assert raised.value.rows == [(102, stored), (107, stored)]

    def test_error_carries_the_first_twenty_of_all_the_refused_values(
        self, old_table, apply_forwards
    ):
        pairs = [(key, "1990-06-14 13:45:37") for key in range(140, 100, -1)]
        state = old_table("conv_many", pairs)
        operation = ConvertPartialDateField("thing", "seen", PartialDateField())

        with pytest.raises(RefusedValuesError) as raised:
            apply_forwards(operation, state)

        assert raised.value.count == 40
        assert [key for key, _ in raised.value.rows] == list(range(101, 121))

    def test_error_is_an_exception_with_no_database_error_in_it(self):
        assert issubclass(RefusedValuesError, Exception)
        assert not issubclass(RefusedValuesError, DatabaseError)

    def test_non_atomic_migration_leaves_the_column_unchanged(
        self, old_table, migrate, read_column, describe_column
    ):
        state = old_table(
            "conv_loose", [(101, "1990-01-01 00:00:00"), (102, "1990-06-14 13:45:37")]
        )
        rows, column = (
            read_column("conv_loose", "seen"),
            describe_column("conv_loose", "seen"),
        )

        with pytest.raises(RefusedValuesError):
            migrate(
                state,
                ConvertPartialDateField("thing", "seen", PartialDateField()),
                atomic=False,
            )

        assert read_column("conv_loose", "seen") == rows
        assert describe_column("conv_loose", "seen") == column

    def test_correcting_the_row_lets_the_migration_complete(
        self, old_table, apply_forwards, read_column
    ):
        state = old_table(
            "conv_fixed", [(101, "1990-01-01 00:00:00"), (102, "1990-06-14 13:45:37")]
        )
        operation = ConvertPartialDateField("thing", "seen", PartialDateField())
        with pytest.raises(RefusedValuesError):
            apply_forwards(operation, state)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE conv_fixed SET seen = %s WHERE id = %s",
                ["1990-06-14 00:00:02", 102],
            )

        apply_forwards(operation, state)

        assert read_column("conv_fixed", "seen") == [(101, "1990"), (102, "1990-06-14")]


STORED_FORMS = [
    "1990-01-01 00:00:00",
    "1990-06-01 00:00:01",
    "1990-06-14 00:00:02",
    "0990-03-01 00:00:01",
    "1800-06-14 00:00:02",
    None,
]


@pytest.mark.django_db(transaction=True)
class TestBackwards:
    @pytest.fixture
    def round_trip(
        self,
        build_state,
        create_tables,
        insert_rows,
        read_column,
        apply_forwards,
        apply_backwards,
    ):
        def run(table, rows, meta=None, **options):
            state = build_state(
                table, {"seen": OldPartialDateField(**options)}, **(meta or {})
            )
            create_tables(state)
            insert_rows(table, "seen", rows)
            stored = read_column(table, "seen")
            operation = ConvertPartialDateField(
                "thing", "seen", PartialDateField(**options)
            )
            converted = apply_forwards(operation, state)
            iso = read_column(table, "seen")
            apply_backwards(operation, state, converted)
            return stored, iso, operation, state

        return run

    @pytest.mark.parametrize("shape", ["nullable", "db_index", "nullable_unique"])
    def test_every_stored_value_comes_back_and_converts_again(
        self, shape, round_trip, read_column, apply_forwards
    ):
        options, _ = SHAPES[shape]
        table = f"back_{shape}"

        stored, iso, operation, state = round_trip(table, STORED_FORMS, **options)

        assert read_column(table, "seen") == stored
        apply_forwards(operation, state)
        assert read_column(table, "seen") == iso

    @pytest.mark.parametrize(("use_tz", "zone"), ZONES)
    def test_values_come_back_in_any_session_zone(
        self, round_trip, read_column, apply_forwards, settings, use_tz, zone
    ):
        settings.USE_TZ = use_tz
        settings.TIME_ZONE = zone

        stored, iso, operation, state = round_trip("back_zone", STORED_FORMS, null=True)

        assert read_column("back_zone", "seen") == stored
        apply_forwards(operation, state)
        assert read_column("back_zone", "seen") == iso

    @pytest.mark.parametrize("shape", SHAPES)
    def test_column_equals_one_created_from_the_stand_in(
        self, shape, round_trip, build_state, create_tables, describe_column
    ):
        options, meta = SHAPES[shape]
        old, new = f"back_{shape}_old", f"back_{shape}_new"
        round_trip(old, ["1990-01-01 00:00:00"], meta(old) if meta else None, **options)
        create_tables(
            build_state(
                new,
                {"seen": OldPartialDateField(**options)},
                **(meta(new) if meta else {}),
            )
        )

        assert describe_column(old, "seen") == describe_column(new, "seen")


@pytest.mark.django_db(transaction=True)
class TestMigrationTooling:
    @pytest.fixture
    def old_table(self, build_state, create_tables, insert_rows):
        state = build_state("tool_rows", {"seen": OldPartialDateField(null=True)})
        create_tables(state)
        insert_rows("tool_rows", "seen", ["1990-01-01 00:00:00", "1990-06-14 13:45:37"])
        return state

    @pytest.mark.parametrize("direction", ["forwards", "backwards"])
    def test_unsupported_vendor_is_refused_with_nothing_changed(
        self,
        direction,
        old_table,
        monkeypatch,
        read_column,
        describe_column,
        apply_forwards,
        apply_backwards,
    ):
        operation = ConvertPartialDateField(
            "thing", "seen", PartialDateField(null=True)
        )
        rows, column = (
            read_column("tool_rows", "seen"),
            describe_column("tool_rows", "seen"),
        )
        target = old_table.clone()
        operation.state_forwards("conv", target)
        with monkeypatch.context() as patch:
            patch.setattr(connection, "vendor", "mysql")
            with pytest.raises(NotSupportedError):
                if direction == "forwards":
                    apply_forwards(operation, old_table)
                else:
                    apply_backwards(operation, old_table, target)

        assert read_column("tool_rows", "seen") == rows
        assert describe_column("tool_rows", "seen") == column

    def test_a_conversion_followed_by_an_alteration_keeps_both(self):
        operations = [
            ConvertPartialDateField("thing", "seen", PartialDateField(null=True)),
            migrations.AlterField(
                "thing", "seen", PartialDateField(null=True, help_text="When seen.")
            ),
        ]

        optimized = MigrationOptimizer().optimize(operations, "conv")

        assert [type(operation) for operation in optimized] == [
            ConvertPartialDateField,
            migrations.AlterField,
        ]

    def test_collecting_sql_reads_no_rows_and_refuses_nothing(
        self, old_table, read_column
    ):
        operation = ConvertPartialDateField(
            "thing", "seen", PartialDateField(null=True)
        )
        rows = read_column("tool_rows", "seen")
        target = old_table.clone()
        operation.state_forwards("conv", target)

        with connection.schema_editor(collect_sql=True) as editor:
            operation.database_forwards("conv", editor, old_table, target)

        assert editor.collected_sql
        assert read_column("tool_rows", "seen") == rows

    def test_the_operation_is_named_for_the_conversion(self):
        field = PartialDateField(null=True)
        operation = ConvertPartialDateField("thing", "seen", field)
        alteration = migrations.AlterField("thing", "seen", field)

        assert operation.describe() != alteration.describe()
        assert operation.migration_name_fragment == "convert_thing_seen"


@pytest.mark.django_db(transaction=True)
class TestBareAlterField:
    def test_generated_alteration_fails_on_a_table_with_rows_and_changes_nothing(
        self,
        build_state,
        create_tables,
        insert_rows,
        apply_forwards,
        read_column,
        describe_column,
    ):
        state = build_state("bare_rows", {"seen": OldPartialDateField(null=True)})
        create_tables(state)
        insert_rows(
            "bare_rows",
            "seen",
            ["1990-01-01 00:00:00", "1990-06-01 00:00:01", "1990-06-14 00:00:02"],
        )
        rows, column = (
            read_column("bare_rows", "seen"),
            describe_column("bare_rows", "seen"),
        )
        operation = migrations.AlterField("thing", "seen", PartialDateField(null=True))

        with pytest.raises(DatabaseError):
            apply_forwards(operation, state)

        assert read_column("bare_rows", "seen") == rows
        assert describe_column("bare_rows", "seen") == column


@pytest.mark.django_db(transaction=True)
class TestMigrationFile:
    def test_operation_deconstructs_with_the_arguments_of_alter_field(self):
        field = PartialDateField(null=True)

        _, args, kwargs = ConvertPartialDateField("m", "f", field).deconstruct()
        _, alter_args, alter_kwargs = migrations.AlterField(
            "m", "f", field
        ).deconstruct()

        assert (args, kwargs) == (alter_args, alter_kwargs)
        assert kwargs["field"].deconstruct() == field.deconstruct()

    def test_written_migration_imports_and_runs(
        self, build_state, create_tables, insert_rows, read_column
    ):
        state = build_state("file_rows", {"seen": OldPartialDateField(null=True)})
        create_tables(state)
        insert_rows("file_rows", "seen", ["1990-01-01 00:00:00", None])
        migration = migrations.Migration("0002_convert", "conv")
        migration.operations = [
            ConvertPartialDateField("thing", "seen", PartialDateField(null=True))
        ]
        source = MigrationWriter(migration).as_string()
        namespace = {}

        exec(compile(source, "0002_convert.py", "exec"), namespace)  # noqa: S102
        written = namespace["Migration"]("0002_convert", "conv")
        with connection.schema_editor() as editor:
            written.apply(state, editor)

        assert [type(operation) for operation in written.operations] == [
            ConvertPartialDateField
        ]
        assert read_column("file_rows", "seen") == [(1, "1990"), (2, None)]
