import re

import pytest
from django.db import DatabaseError, connection, migrations, models, transaction
from django.db.migrations.state import ModelState, ProjectState

from partial_dates import PartialDateField
from partial_dates.conversion import ConvertPartialDateField, OldPartialDateField
from tests.factories import EventFactory, RecordFactory, SampleFactory

SEEK = re.compile(r"SEARCH .* USING|Index (Only )?Scan")
WALK = re.compile(r"USING (COVERING )?INDEX|Index (Only )?Scan")


@pytest.fixture
def record(db):
    return RecordFactory()


@pytest.fixture
def event(db):
    return EventFactory()


@pytest.fixture
def sample(db):
    return SampleFactory()


@pytest.fixture
def grid(db):
    texts = [
        "1990",
        "1990-05",
        "1990-05-31",
        "1990-06",
        "1990-06-01",
        "1990-06-14",
        "1990-07",
        "1991",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]


@pytest.fixture
def spread(db):
    texts = [
        "9999-12-31",
        "1990-06-14",
        "1991",
        "0001",
        "1990",
        "1990-06",
        "2000-02-29",
        "1990-06-01",
        "0990",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]


@pytest.fixture
def starts(db):
    texts = [
        "0001",
        "1990",
        "1990-01",
        "1990-01-01",
        "1990-06",
        "1990-06-01",
        "1990-06-14",
        "2000-02-29",
        "9999-12-31",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]


@pytest.fixture
def found():
    def texts(queryset, *ordering):
        return [
            None if sample.collected is None else str(sample.collected)
            for sample in queryset.order_by(*(ordering or ("pk",)))
        ]

    return texts


@pytest.fixture
def query_plan(db):
    def plan(queryset):
        if connection.vendor == "postgresql":
            # A small table would otherwise hide a query that has no index path.
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL enable_seqscan = off")
        return queryset.explain()

    return plan


@pytest.fixture
def seeks_index(query_plan):
    def check(queryset):
        return bool(SEEK.search(query_plan(queryset)))

    return check


@pytest.fixture
def walks_index(query_plan):
    def check(queryset):
        return bool(WALK.search(query_plan(queryset)))

    return check


@pytest.fixture
def guide_samples(db):
    texts = [
        "1990",
        "1990-05",
        "1990-05-31",
        "1990-06",
        "1990-06-01",
        "1990-06-14",
        "1990-07",
        "1990-12",
        "1991",
        "1991-03",
        "1991-03-15",
        "1991-04",
        "1991-06",
        "1991-06-02",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]


APP = "conv"
GOOD_TEXTS = ["0002", "0002-02", "0002-02-02"]
BAD_TEXTS = ["0002-13", "0002-02-30", "garbage", "0002-02-02 00:00:00", "00020202"]


@pytest.fixture
def build_state():
    def build(table, fields, name="Thing", state=None, **options):
        state = state or ProjectState()
        state.add_model(
            ModelState(
                APP,
                name,
                [("id", models.AutoField(primary_key=True)), *fields.items()],
                {"db_table": table, **options},
            )
        )
        return state

    return build


@pytest.fixture
def create_tables():
    created = []

    def create(state):
        with connection.schema_editor() as editor:
            for model in state.apps.get_models():
                if model._meta.app_label == APP:
                    editor.create_model(model)
                    created.append(model._meta.db_table)

    yield create

    with connection.cursor() as cursor:
        for table in created:
            cursor.execute(f"DROP TABLE IF EXISTS {connection.ops.quote_name(table)}")


@pytest.fixture
def insert_rows():
    def insert(table, column, values):
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            for value in values:
                cursor.execute(
                    f"INSERT INTO {quote(table)} ({quote(column)}) VALUES (%s)",
                    [value],
                )

    return insert


@pytest.fixture
def read_column():
    def read(table, column):
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT id, CAST({quote(column)} AS TEXT) FROM {quote(table)} "
                "ORDER BY id"
            )
            return cursor.fetchall()

    return read


@pytest.fixture
def apply_forwards():
    def apply(operation, state):
        target = state.clone()
        operation.state_forwards(APP, target)
        with connection.schema_editor() as editor:
            operation.database_forwards(APP, editor, state, target)
        return target

    return apply


@pytest.fixture
def check_behaviour():
    def probe(table, column):
        quote = connection.ops.quote_name
        sql = f"INSERT INTO {quote(table)} ({quote(column)}) VALUES (%s)"
        accepted = {}
        for text in [*GOOD_TEXTS, *BAD_TEXTS]:
            try:
                with transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(sql, [text])
                    transaction.set_rollback(True)
                accepted[text] = True
            except DatabaseError:
                accepted[text] = False
        return accepted

    return probe


@pytest.fixture
def describe_column(check_behaviour):
    def describe(table, column):
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute(
                    "SELECT data_type, character_maximum_length, collation_name, "
                    "is_nullable FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = %s",
                    [table, column],
                )
                kind, length, collation, nullable = cursor.fetchone()
                cursor.execute(
                    "SELECT indexdef FROM pg_indexes WHERE tablename = %s", [table]
                )
                indexes = sorted(
                    re.sub(r"^CREATE (UNIQUE )?INDEX \S+ ON \S+ ", r"\1", row[0])
                    for row in cursor.fetchall()
                )
            else:
                cursor.execute(f"PRAGMA table_info({quote(table)})")
                info = next(row for row in cursor.fetchall() if row[1] == column)
                kind, nullable = info[2], "NO" if info[3] else "YES"
                length = collation = None
                indexes = []
                cursor.execute(f"PRAGMA index_list({quote(table)})")
                for _, name, unique, _, _ in cursor.fetchall():
                    cursor.execute(f"PRAGMA index_info({quote(name)})")
                    columns = tuple(row[2] for row in cursor.fetchall())
                    indexes.append((unique, columns))
                indexes.sort()
        return {
            "type": kind,
            "length": length,
            "collation": collation,
            "nullable": nullable,
            "indexes": indexes,
            "check": check_behaviour(table, column),
        }

    return describe


@pytest.fixture
def convert(build_state, create_tables, insert_rows, apply_forwards):
    def run(table, rows, meta=None, **options):
        state = build_state(
            table, {"seen": OldPartialDateField(**options)}, **(meta or {})
        )
        create_tables(state)
        insert_rows(table, "seen", rows)
        operation = ConvertPartialDateField(
            "thing", "seen", PartialDateField(**options)
        )
        return apply_forwards(operation, state)

    return run


@pytest.fixture
def insert_keyed():
    def insert(table, column, pairs):
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            for key, value in pairs:
                cursor.execute(
                    f"INSERT INTO {quote(table)} (id, {quote(column)}) VALUES (%s, %s)",
                    [key, value],
                )

    return insert


@pytest.fixture
def migrate():
    def run(state, *operations, atomic=True):
        migration = migrations.Migration("0001_convert", APP)
        migration.operations = list(operations)
        migration.atomic = atomic
        with connection.schema_editor(atomic=atomic) as editor:
            return migration.apply(state, editor)

    return run


@pytest.fixture
def apply_backwards():
    def apply(operation, old_state, new_state):
        with connection.schema_editor() as editor:
            operation.database_backwards(APP, editor, new_state, old_state)
        return old_state

    return apply
