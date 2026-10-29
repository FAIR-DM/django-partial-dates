# Implementation Plan: Storing a partial date on a model

**Branch**: `002-model-field` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: `specs/002-model-field/spec.md`, `research.md`

## Summary

One new module, `partial_dates/fields.py`, holding `PartialDateField`, a `models.Field` subclass
whose column is `varchar(10)`, byte-order collated and guarded by its own column check. It takes
and gives back FS-001's `PartialDate`. The package re-exports it. A test app with one migration
holds the test models. The test settings pick SQLite or PostgreSQL from the environment. Django
becomes the package's runtime dependency.

## Technical context

- **Language**: Python 3.12 and later. Django 5.2 LTS, 6.0 and 6.1
- **Runtime dependencies**: `django>=5.2`, new (research R8)
- **Development dependencies**: `psycopg[binary]>=3.2`, new, for the PostgreSQL test run
  (research R5). Added in the plan commit
- **Testing**: pytest-django, against SQLite by default and PostgreSQL with
  `TEST_DATABASE=postgresql`
- **Constraints**: one column, no companion (ADR 0001, Article XI). Same behaviour on both
  databases (FR-011)

## Constitution check

| Article | How the plan meets it |
|---|---|
| I Testing | Test-first per task. Validation asserted by field and code, never by message. Raw SQL tests assert the database's error type |
| II Simplicity | One class, on Django's own column check, collation parameter and serialiser hooks. The check SQL is the only new mechanism |
| III Anti-abstraction | No base class, mixin or registry |
| IV Integration-first | Every test goes through a model, the ORM, raw SQL or a management command |
| V Security | Text from outside reaches the column only through `PartialDate.fromisoformat` or the database check. Raw SQL in tests is parameterised |
| VI Documentation | README *Usage* gains the field, empty values and fixtures. CHANGELOG entry |
| VII Dependencies | Django at runtime, declared with the first module importing it. psycopg for tests only. `deptry` green |
| VIII i18n | The field description and the `invalid` message use `gettext_lazy`. Base English catalog under `partial_dates/locale/` |
| IX Data model | The package defines no model. Indexing is the developer's choice (D6). The test models are not shipped |
| X Cohesion | All behaviour is on the field class |
| XI Storage | The ISO form in one column, `C` collation, check constraint |
| XII Filters | Not applicable: `exact` only. R3 adds lookups |
| XIII Compatibility | Django 5.2 and later, PostgreSQL and SQLite |

No violations.

## Design

### Public names

`partial_dates/__init__.py` re-exports `PartialDateField` from `partial_dates.fields` and lists
it in `__all__` beside the FS-001 names.

### `PartialDateField(models.Field)`

| Member | Behaviour | Requirement |
|---|---|---|
| `description` | `gettext_lazy` text | VIII |
| `empty_strings_allowed = False` | default is `None`, never `""` | FR-005 |
| `default_error_messages` | `{"invalid": gettext_lazy(...)}` | FR-008 |
| `__init__(*args, **kwargs)` | refuses a `max_length` argument with `TypeError`; sets `max_length = 10` | FR-002 |
| `deconstruct()` | drops `max_length`, and writes a `PartialDate` default as its ISO form so a migration can record it | FR-004, FR-009 |
| `get_internal_type()` | `"CharField"` | FR-002 |
| `db_parameters(connection)` | the parent's, with `collation = "C"` when `connection.vendor == "postgresql"` | FR-002 |
| `db_check(connection)` | the check SQL of research R3, built from `connection.ops.quote_name(self.column)`. On SQLite only, it also requires `LENGTH(CAST(col AS BLOB)) = LENGTH(col)`, which refuses text with an embedded NUL | FR-003 |
| `from_db_value(value, expression, connection)` | research R4 | FR-006 |
| `to_python(value)` | research R4; `ValidationError(self.error_messages["invalid"], code="invalid", params={"value": value})` | FR-008 |
| `get_prep_value(value)` | research R4 | FR-005, FR-007, FR-010 |
| `value_to_string(obj)` | the field's value through `get_prep_value`, so an instance still holding unvalidated text writes its ISO form | FR-013 |

The check SQL is assembled inside `db_check` from local expressions: a digit test per position,
the year, month and day casts, the days in the month. No module-level helper, no name with a
leading underscore.

### Test app

- `INSTALLED_APPS` gains `"tests"`. No app config file.
- `tests/models.py`:
  - `Record`: `date = PartialDateField(null=True, blank=True)` and
    `other = PartialDateField(null=True, blank=True)` (two fields on one model, an edge case),
    `defaulted = PartialDateField(default="1990")`
  - `Event`: `occurred = PartialDateField(unique=True)` (requires a date, no default),
    `indexed = PartialDateField(db_index=True, null=True, blank=True)`
- Every test-model field has a `verbose_name` and `help_text` (testing standard §5).
- `tests/factories.py`: `RecordFactory` and `EventFactory`, `Event.occurred` from a `factory.Sequence` of distinct ISO forms. `tests/conftest.py` holds fixtures wrapping them. `tests/test_factories.py` mirrors the factories module.
- `tests/migrations/0001_initial.py`, made with `makemigrations tests`.
- `tests/fixtures/records.json`, `records.jsonl`, `records.xml`: rows at each precision and one
  empty, exactly as `dumpdata` writes them (research R7).

### Test settings

`tests/settings.py`: `INSTALLED_APPS = ["django.contrib.contenttypes", "tests"]`. `DATABASES`
chosen by `TEST_DATABASE` (research R5). `USE_TZ` stays.

### Tests

`tests/test_fields.py` mirrors `partial_dates/fields.py`, classes by subject:

| Class | Covers |
|---|---|
| `TestColumn` | US-1 1, 2: column type, length, collation (PostgreSQL) and check, read through `connection.introspection`; `makemigrations --check --dry-run` clean; `deconstruct()` has no `max_length`; `max_length` refused |
| `TestDatabaseCheck` | US-1 11, 12 and the edge cases: raw parameterised `INSERT` and `UPDATE` per text. Overlong text accepts `IntegrityError` or `DataError` |
| `TestSavingAndReading` | US-1 3–7 and 14 |
| `TestRefusedWrites` | US-1 8 through `save()`, `create()`, `update()`, `bulk_create()` and `bulk_update()`, rows unchanged afterwards |
| `TestValidation` | US-1 9, 10 |
| `TestFiltering` | US-1 13 |
| `TestFixtures` | US-2 1–7, parametrised over `json`, `jsonl` and `xml` |

`tests/test_init.py` gains `TestImportWithoutSettings` for FR-012: a fresh interpreter with
`DJANGO_SETTINGS_MODULE` removed imports `partial_dates` and builds a value. `tests/test_models.py`
holds the one parametrised `verbose_name` and `help_text` check over every test-model field.

US-1 scenario 15 and SC-004 are the whole suite run twice, with and without
`TEST_DATABASE=postgresql`, before review. Both results go in the pull request.

## Documentation

- README: *Status* says the field exists. *Usage* gains the field: declaring it, what it takes and
  gives back, empty values, that the database refuses malformed text, and fixtures.
- CHANGELOG `[Unreleased]` → *Added*: the field. *Changed*: Django is now a dependency.
- `specs/001-partial-date-value/spec.md`: FR-006 and SC-005 rewritten as D8 says, in the plan
  commit.
- `docs/ROADMAP.md`: R2's status line, at ready for review.

## Project structure

```text
partial_dates/
├── __init__.py                        re-exports PartialDateField
├── fields.py                          new
└── locale/en/LC_MESSAGES/django.po    new
tests/
├── settings.py                        database from the environment, the test app
├── models.py                          new
├── factories.py, conftest.py          new
├── test_factories.py, test_models.py  new
├── migrations/0001_initial.py         new
├── fixtures/records.{json,jsonl,xml}  new
└── test_fields.py                     new
pyproject.toml                         django dependency, non-mirror paths
README.md, CHANGELOG.md
```

## Stories and dispatch

Two stories, three dispatch groups, in order on the feature branch:

- US-1 group 1: settings, test app, the column and its check (T001–T003)
- US-1 group 2: conversions, refused writes, validation, filtering, import, docs (T004–T008)
- US-2: fixtures and their docs (T009–T010)
