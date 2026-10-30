import ast
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from partial_dates import PartialDate
from tests.moving.models import Sighting, Survey

APP_DIR = Path(__file__).parent / "moving"
LATEST = ("moving", "0004_convert_dates")
BEFORE = ("moving", "0003_add_note")
FIRST = ("moving", "0001_initial")
EMPTY = ("moving", None)

# What the old field stored: midnight for a year, one second for a month and two
# for a day.
STORED = [
    "1990-01-01 00:00:00",
    "1990-06-01 00:00:01",
    "1990-06-14 00:00:02",
    None,
]
CONVERTED = ["1990", "1990-06", "1990-06-14", None]

SUBJECTS = [
    pytest.param(Sighting, "seen_on", "observed", True, id="rename-and-alteration"),
    pytest.param(Survey, "taken", "taken", False, id="subclass"),
]


@pytest.fixture
def migrate_to(transactional_db):
    def go(target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])

    yield go

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.fixture
def pending():
    def names():
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        return [(migration.app_label, migration.name) for migration, _ in plan]

    return names


@pytest.fixture
def write_old_rows():
    def write(model, column, nullable):
        quote = connection.ops.quote_name
        sql = f"INSERT INTO {quote(model._meta.db_table)} ({quote(column)}) VALUES (%s)"
        with connection.cursor() as cursor:
            for value in STORED[: None if nullable else -1]:
                cursor.execute(sql, [value])

    return write


@pytest.fixture
def read_dates():
    def read(model, attribute):
        return [
            None if value is None else str(value)
            for value in model.objects.order_by("pk").values_list(attribute, flat=True)
        ]

    return read


@pytest.fixture
def schemas(describe_column):
    def describe():
        return {
            model: describe_column(model._meta.db_table, column)
            for model, column in [(Sighting, "seen_on"), (Survey, "taken")]
        }

    return describe


@pytest.fixture
def new_columns(build_state, create_tables, describe_column):
    state = build_state(
        "fresh_sighting",
        {"seen_on": Sighting._meta.get_field("observed").clone()},
        name="Sighting",
    )
    build_state(
        "fresh_survey",
        {"taken": Survey._meta.get_field("taken").clone()},
        name="Survey",
        state=state,
    )
    create_tables(state)
    return {
        Sighting: describe_column("fresh_sighting", "seen_on"),
        Survey: describe_column("fresh_survey", "taken"),
    }


class TestApp:
    def test_makemigrations_finds_nothing_to_make(self, db):
        call_command("makemigrations", "moving", check=True, dry_run=True)

    def test_nothing_imports_the_old_package(self):
        imported = set()
        for path in APP_DIR.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])

        assert "partial_date" not in imported
        assert "partial_dates" in imported


class TestDatabases:
    @pytest.mark.parametrize(("model", "column", "attribute", "nullable"), SUBJECTS)
    def test_new_database_has_the_column_a_new_table_gets(
        self, migrate_to, schemas, new_columns, model, column, attribute, nullable
    ):
        migrate_to(EMPTY)
        migrate_to(LATEST)

        schema = schemas()[model]

        assert schema == new_columns[model]
        assert schema["check"]["0002-02"] is True
        assert schema["check"]["garbage"] is False

    @pytest.mark.parametrize(("model", "column", "attribute", "nullable"), SUBJECTS)
    def test_deployed_database_runs_only_the_conversion(
        self,
        migrate_to,
        pending,
        write_old_rows,
        read_dates,
        model,
        column,
        attribute,
        nullable,
    ):
        migrate_to(BEFORE)
        write_old_rows(model, column, nullable)

        assert pending() == [LATEST]
        migrate_to(LATEST)

        assert read_dates(model, attribute) == CONVERTED[: None if nullable else -1]

    @pytest.mark.parametrize(("model", "column", "attribute", "nullable"), SUBJECTS)
    def test_database_behind_converts_through_the_rebuild(
        self, migrate_to, write_old_rows, read_dates, model, column, attribute, nullable
    ):
        migrate_to(FIRST)
        write_old_rows(model, column, nullable)

        migrate_to(LATEST)

        assert read_dates(model, attribute) == CONVERTED[: None if nullable else -1]

    @pytest.mark.parametrize("start", [BEFORE, FIRST], ids=["0003", "0001"])
    def test_every_route_ends_on_the_same_schema(
        self, migrate_to, write_old_rows, schemas, start
    ):
        migrate_to(EMPTY)
        migrate_to(LATEST)
        from_empty = schemas()

        migrate_to(start)
        write_old_rows(Sighting, "seen_on", True)
        write_old_rows(Survey, "taken", False)
        migrate_to(LATEST)

        assert schemas() == from_empty
