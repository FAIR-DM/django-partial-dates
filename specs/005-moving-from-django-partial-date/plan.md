# Implementation Plan: Moving from django-partial-date

**Branch**: `005-moving-from-django-partial-date` | **Date**: 2026-10-30 | **Spec**: `spec.md`

## Summary

One new module, `partial_dates/conversion.py`, holds a migration operation and a stand-in field. A
how-to guide, an ADR and a test app whose migrations follow the guide carry the rest.

## Technical Context

- **Language and stack**: Python 3.12+, Django 5.2 and 6.x, PostgreSQL and SQLite
- **Dependencies**: none added, and django-partial-date stays out of the runtime and dev groups
- **Testing**: pytest with `pytest.mark.django_db(transaction=True)` wherever a schema editor runs

## Constitution Check

| Article | How the plan meets it |
|---|---|
| II, III Simplicity | One operation subclassing `AlterField`, one field, one helper field. No base class, no registry |
| VII Dependencies | None added |
| IX Migrations | The test app's migrations are fixtures for the feature, and are not squashed |
| X Cohesion | The parsing and SQL are methods on the operation |
| XI Storage | The operation ends at the column ADR 0001 sets out |
| XIII Stack | Both databases tested, and any other refused |

## Design

### `partial_dates/conversion.py`

```python
class RefusedValuesError(Exception): ...        # refused values, with the error FR-007 asks for
class OldPartialDateField(models.Field): ...    # the stand-in
class ConvertPartialDateField(migrations.AlterField): ...
```

**`OldPartialDateField`** subclasses `models.Field`.

- `get_internal_type()` returns `"CharField"`, with a comment saying why (`research.md`, "The
  stand-in field makes that mistake loud").
- `db_type()` returns `connection.data_types["DateTimeField"]`.
- `db_check()` returns `None`.
- It takes every `Field` option, with no `max_length`, and writes values through unchanged.

**`ConvertPartialDateField`** subclasses `migrations.AlterField`, so it has the same arguments and
state handling. `database_forwards`:

1. Return if `allow_migrate_model` says no.
2. Raise `django.db.NotSupportedError` on a vendor other than `postgresql` and `sqlite`.
3. Unless `schema_editor.collect_sql`, read `pk` and the stored text ordered by primary key, and
   raise `RefusedValuesError` if any value is refused. The stored text is `col::timestamp::text` on
   PostgreSQL and `CAST(col AS TEXT)` on SQLite. A bare read of a `datetime` column on SQLite goes
   through Django's converter, which gives `None` for junk text, so the cast is what lets a refused
   value be seen. Only `NULL` is skipped. "The first" refused values are the lowest primary keys.
4. Run the steps in `research.md` for the vendor.

A stored value converts when it is text fully matching
`[0-9]{4}-[0-9]{2}-[0-9]{2} 00:00:0[012]`, the date is one `PartialDate(year, month, day)` accepts,
and the seconds agree with it: 0 needs month and day 1, 1 needs day 1. A value that `PartialDate` refuses is
refused. A number on SQLite casts to text that does not match.

`RefusedValuesError` gives the model, the field, the count, and the primary key and stored value of
the first 20.

The rewrite is one expression on the stored text `t`, the same on both databases:

```sql
CASE SUBSTR(t, 19, 1) WHEN '0' THEN SUBSTR(t, 1, 4)
                      WHEN '1' THEN SUBSTR(t, 1, 7)
                      ELSE SUBSTR(t, 1, 10) END
```

and one on the way back, on the column `c`:

```sql
CASE LENGTH(c) WHEN 4 THEN c || '-01-01 00:00:00'
               WHEN 7 THEN c || '-01 00:00:01'
               ELSE c || ' 00:00:02' END
```

`database_backwards` runs the steps in reverse: `alter_field(new, new without indexes)`, then on
PostgreSQL one `ALTER TABLE` dropping the check and changing the type to the timestamp type `USING
(<expression>)::timestamp with time zone`, or on SQLite `alter_field` to the unchecked field, the
`UPDATE`, and `alter_field` to the old field without indexes. Last, `alter_field(old without
indexes, old)`. It reads no values and refuses none.

The old field without indexes is a clone with `db_index=False` and `unique=False`. The middle
field is a `models.CharField(max_length=10)` with no index and the old field's `null`, so
`alter_field` makes any change of `null` in its last step. Both carry `name`, `column` and `model`.
The operation's helpers are `refused_values`, `old_without_indexes` and `plain_text_field`, with no
leading underscore on any name.

The check's name is `truncate_name(f"{table}_{column}_check", max_name_length)`, passed through
`quote_name`, used to add and to drop it. On a name over the database's limit it differs from the
name PostgreSQL would give a new column, which changes nothing a developer sees.

`reduce` returns `False`. `describe` and `migration_name_fragment` name the conversion.

The check's SQL comes from `new_field.db_check(connection)`. It contains no `%`, and the statements
are run with `params=None`.

### Documentation

- `docs/developer/moving-from-django-partial-date.md`, the guide, covering FR-015 to FR-017, the
  `AlterField` warning, that `sqlmigrate` output carries no check, that the conversion needs an
  atomic migration for a failure after its first step to leave everything in place, and that a
  change of `null` belongs in its own alteration, linked from `docs/developer/index.md`
- `docs/adr/0002-*.md`, recording D2 and D5, with the rejected alternatives. The number is checked
  against origin/main when the branch is pushed
- `CONTEXT.md`: **old column**, **conversion**, **refused value**, **stand-in field**
- `README.md` and `CHANGELOG.md`
- `docs/ROADMAP.md`: R5 marked delivered, as R3 was, with the links to its issues

## Test design

`tests/test_conversion.py` builds an old column with `ModelState` and `OldPartialDateField`, writes
rows through raw SQL, and applies the operation with `database_forwards` and `database_backwards`.
No test asserts wording: an error is tested by its type and by the keys and values it names.

`tests/moving/` is a test app, in `INSTALLED_APPS` in `tests/settings.py`, whose migrations are the
guide's end state. Each migration is a line in User Story 2:

| Migration | Does |
|---|---|
| `0001` | Creates `Sighting` (nullable, indexed, `db_column`) and `Survey` (required, through a project's own subclass, on an abstract base), both with `OldPartialDateField` |
| `0002` | Alters a help text and renames the field on `Sighting` |
| `0003` | Adds a column to both, which rebuilds the table on SQLite |
| `0004` | The conversions |

`tests/test_moving.py` migrates with `MigrationExecutor`: back to each step with raw rows, then
forward, and compares schemas with a new database. `makemigrations --check` covers the app.
`tests/test_guide.py` gains a class for the new guide. The guide's end-state migration and model
blocks each name the `tests/moving` file they mirror, and the test asserts each block equals that
file's text, so the guide and the test app are one source. Other Python blocks run, and blocks
showing the state before the move are marked as not run.

Every test runs on both databases through `TEST_DATABASE`, which is how the suite already works.

## Complexity Tracking

| Exception | Why |
|---|---|
| Raw SQL in a package | `alter_field` has no way to pass a `USING` (`research.md`). Table, column and constraint names go through `quote_name`, and no value is interpolated. There is no injection route. The check in Python is what guards against truncation, so the guide says the output of `sqlmigrate` carries no check and writes must stop during the move |
| `get_internal_type()` that does not match the column | It is the one way to stop Django's alteration truncating values silently |
