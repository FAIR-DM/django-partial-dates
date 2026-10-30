# Research — FS-002: Storing a partial date on a model

Investigated against `main` at `e2b05cf` (FS-001 merged), Django 6.1.2 in the lock file, and
PostgreSQL 17 and SQLite 3 run locally. There is no `planning-notes.md` and no sketch.

## R1 — The field subclasses `models.Field`, not `models.CharField`

`CharField.__init__` appends a `MaxLengthValidator`, which calls `len()` on the cleaned value. The
cleaned value here is a `PartialDate`, which has no length, so `full_clean()` would raise
`TypeError`. `CharField.to_python()` also turns any value into `str`, the opposite of what this
field needs.

`models.Field` with `get_internal_type()` returning `"CharField"` gets the `varchar(%(max_length)s)`
column type from every backend's `data_types` table, with `max_length` fixed at 10, and none of
`CharField`'s conversions. `Field.formfield()` already passes `max_length` to the form field, so a
model form shows a plain text input of the right length until R4.

`deconstruct()` drops `max_length`, so a developer never passes it and a migration never records
it. Passing it is refused by `__init__`.

## R2 — The collation is set per backend in `db_parameters()`

`CharField(db_collation=...)` writes one collation name for every backend. PostgreSQL's byte-order
collation is `"C"`. SQLite has no collation by that name and already compares text byte by byte
(`BINARY`), so a fixed `db_collation="C"` fails on SQLite.

The schema editor reads `field.db_parameters(connection)["collation"]` when it creates or alters a
column (`BaseDatabaseSchemaEditor.column_sql` and `_alter_column_collation_sql`). The field returns
`"C"` there when `connection.vendor == "postgresql"` and nothing otherwise. Because the collation
is not a constructor argument, it never appears in `deconstruct()` or in a migration, and a second
`makemigrations` finds nothing to change (FR-004).

Verified on PostgreSQL 17: `information_schema.columns.collation_name` is `C` for the column.

## R3 — The check is the field's own column check, `db_check()`

Django already gives a field a column-level check through `Field.db_check(connection)`, which is
how `PositiveIntegerField` gets `"col" >= 0`. The schema editor puts the returned SQL in the column
definition, as `CHECK (...)`, on `CreateModel`, `AddField` and SQLite's table rebuild. PostgreSQL
names it `<table>_<column>_check`, so two fields on one model never collide.

So the developer declares nothing: no `Meta.constraints`, no extra field (SC-005).

The SQL the field returns must be portable and must not depend on evaluation order:

- **No `%`.** Column SQL can be executed with parameters, where a bare `%` is a placeholder.
  Remainders are written as `y - (y / 4) * 4`, integer division on both backends.
- **No casting before the shape is known.** PostgreSQL does not promise to evaluate `AND` left to
  right, and `CAST('1a' AS INTEGER)` raises there instead of giving `0` as SQLite does. `CASE`
  evaluates its branches in order on both, so the shape is tested in the `WHEN` and the numbers
  only in the `THEN`.
- **`NULL` passes explicitly.** A `CASE` with an `ELSE FALSE` turns `NULL` into false, which
  refused `NULL` on SQLite in the trial. The check is `col IS NULL OR CASE ... END`.
- **An embedded NUL is refused on SQLite.** SQLite's `LENGTH()` counts characters up to the
  first NUL, so `1990`, a NUL, then `junk` passes the length test (reproduced on SQLite 3.53.1).
  The SQLite arm adds `LENGTH(CAST(col AS BLOB)) = LENGTH(col)`, equal for every accepted form.
  `CAST AS BLOB` is not PostgreSQL, so `db_check` branches on `connection.vendor`. PostgreSQL text
  cannot hold a NUL at all, and the driver refuses it before the query runs.
- **Digits are tested one character at a time** with `SUBSTR(col, i, 1) BETWEEN '0' AND '9'`,
  which is byte order on both and rejects non-ASCII digits.

Shape:

```sql
"col" IS NULL OR CASE
  WHEN LENGTH("col") = 4 AND <4 digits> THEN <year is not 0000>
  WHEN LENGTH("col") = 7 AND <digits> AND <hyphen at 5> THEN <year> AND <month 1-12>
  WHEN LENGTH("col") = 10 AND <digits> AND <hyphens at 5 and 8>
    THEN <year> AND <month 1-12> AND <day 1 to days in month, Gregorian leap years>
  ELSE FALSE
END
```

Trial, on both backends through raw `INSERT`s: every valid form in the spec, including `0001`,
`9999-12-31`, `2000-02-29` and `1996-02-29`, is accepted, and `NULL` is accepted. Every refused text
in US-1 scenario 11 is refused, as are `1990-00`, `1990-06-00`, `1990-06-32`, `199a`, `1990/06`
and Arabic-Indic digits. SQLite raises `IntegrityError` for each. PostgreSQL raises
`IntegrityError` for each except text longer than ten characters, which the `varchar(10)` column
refuses first with `DataError`. Both are the database refusing the write (US-1 scenario 11), so
tests accept either for overlong text.

## R4 — Conversions

| Method | Gets | Returns |
|---|---|---|
| `from_db_value` | `None` or the stored text | `None`, or `PartialDate.fromisoformat(text)` |
| `to_python` | anything | `None` for `None` and `""`; a `PartialDate` unchanged; anything else through `PartialDate.fromisoformat`, its `ValueError` re-raised as `ValidationError(code="invalid")` |
| `get_prep_value` | anything | `None` for `None` and `""`; `PartialDate` → `isoformat()`; anything else through `PartialDate.fromisoformat(value).isoformat()`, so the value's `ValueError` is raised before any query runs |
| `value_to_string` | the instance | the field's value through `get_prep_value`: the ISO form, or `None` |

`get_prep_value` is called for every ORM write (`save()`, `create()`, `update()`, `bulk_create()`,
`bulk_update()`) and for lookup values, so exact-match filtering by a `PartialDate` or its ISO
form works with no lookup code (FR-010). `PartialDate.fromisoformat` already refuses a non-`str`
with `ValueError` (FS-001 D3), which covers a real date or a number (US-1 scenario 8).

A `PartialDate` given as a default cannot be written to a migration: the migration serialiser
knows no frozen dataclass. `deconstruct()` therefore writes such a default as its ISO form, which
`get_prep_value` reads back the same way.

`empty_strings_allowed = False`, as on Django's `DateField`. `get_default()` then gives `None`
instead of `""`, and the column never holds empty text.

Django's serialisers call `value_to_string` for any value that is not a protected type, and write
`None` as `null` in JSON and JSON Lines and as `<None/>` in XML. On loading, they call
`to_python`, and a `ValidationError` there stops `loaddata` with a `DeserializationError`. No
serialiser code is needed beyond `value_to_string`.

## R5 — The test database comes from the environment

`tests/settings.py` reads `TEST_DATABASE`. Unset or `sqlite`, the suite uses SQLite in memory, as
now. `postgresql` uses the PostgreSQL backend with `NAME`, `USER`, `PASSWORD`, `HOST` and `PORT`
from the standard `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST` and `PGPORT` variables. #9 then
only has to start a database service and set them.

The PostgreSQL backend needs a driver. `psycopg[binary]` 3 is added as a development dependency
only (Constitution Article VII: a test-only need, no runtime effect). The shared toolchain bundle
does not carry it.

## R6 — A test app holds the test models

The tests need concrete models. `tests` becomes an installed app with `tests/models.py` and a
committed `tests/migrations/0001_initial.py`, so the suite migrates the way a project would, and
a test can run `makemigrations --check` against it (US-1 scenarios 1 and 2). `tests/models.py`,
`tests/migrations/` and `tests/fixtures/` go in the conformance `non-mirror-paths` list beside
`tests/test_init.py`: they belong to no source module.

## R7 — Fixtures across databases

One suite run has one database, so "dump from SQLite, load into PostgreSQL" (US-2 scenario 7) is
proved in two halves. A fixture committed under `tests/fixtures/`, holding values at every
precision and an empty one, is exactly what `dumpdata` writes for those rows. On each backend the
suite loads it and compares the rows, and dumps the same rows and compares the output with the
file. Run on both backends, that shows each one writes what the other reads.

## R8 — Django becomes a runtime dependency

`dependencies = ["django>=5.2"]`, the lowest supported release in the constitution's stack
article, declared with the first module that imports it, as the `pyproject.toml` comment asks.
`partial_dates/__init__.py` re-exports the field beside the value. Importing `django.db.models`
needs no configured settings, so `import partial_dates` and `PartialDate(1990)` still work with
none (FR-012). A test runs that in a fresh interpreter with `DJANGO_SETTINGS_MODULE` unset.

## R9 — Translations

The field's `description` and the `invalid` error message are the package's first user-facing
strings. Both are wrapped with `gettext_lazy`. Constitution Article VIII then asks for a `locale/`
directory with a base English catalog: `partial_dates/locale/en/LC_MESSAGES/django.po`, made with
`makemessages -l en` from inside `partial_dates/`. Without an app config, Django finds a package's
translations only when the package is installed as an app, so the catalog is there for projects
that compile or extend it, as the article puts it. The field adds no app config (R1 of the
existing-first list: nobody asked for one).

## R10 — What R3 inherits

The field inherits every lookup Django registers on `Field`, the text-pattern ones (`contains`,
`startswith` and the rest) included. Comparison lookups pass their value through
`get_prep_value`, so a bound that is not a partial date is refused. Pattern lookups do not. Which
lookups R3 keeps, and what each matches, is R3's. This feature tests `exact` alone.

On PostgreSQL, `db_index=True` on a `varchar` column with a deterministic collation also creates
a `varchar_pattern_ops` index. With the `C` collation the plain index already serves prefix
matches, so the second one is redundant. Whether the field suppresses it is left to R3, which is
where prefix matches arrive.

## What already exists

| Piece | Where the search stopped |
|---|---|
| Parsing and validating the ISO form | This repo: `PartialDate.fromisoformat` (FS-001) |
| The column type | Django: `data_types["CharField"]` on every backend |
| The collation | Django: `db_parameters()["collation"]`, read by the schema editor |
| The database check | Django: `Field.db_check()`, put in the column definition by the schema editor. The SQL it returns is new code |
| Serialisation and fixture loading | Django: `value_to_string` and `to_python`, called by `django.core.serializers` |
| Validation errors with a code | Django: `ValidationError(code=...)`, raised from `to_python` |
| Exact-match filtering | Django: the `exact` lookup through `get_prep_value` |
| Selecting the test database | New code: five `os.environ` reads in `tests/settings.py` |
| The PostgreSQL driver for tests | A maintained package: `psycopg` 3, development only |
